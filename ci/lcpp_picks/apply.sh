#!/bin/bash
# ci/lcpp_picks/apply.sh -- 把「已采纳」的上游补丁按梯子顺序打到一棵 llama.cpp 树上。
#
#   apply.sh <llama.cpp 目录>            # 只打 status=ADOPTED 的行
#   apply.sh <llama.cpp 目录> --all      # 打 TESTING + ADOPTABLE + ADOPTED（复现实验臂）
#   apply.sh <llama.cpp 目录> --upto 5   # 打到梯子第 5 步（复现某个检查点）
#
# host 文件（mmq.cu / moe_mmq.cu）被 --exclude 掉：它们不在我们的编译面里，
# 我们有 src/prefill/ 下的粘合层，按 mmq_args 的槽位喂参数。
set -u
DIR=${1:?usage: apply.sh <llama.cpp dir> [--all|--upto N]}
MODE=${2:-adopted}
UPTO=${3:-999}
HERE=$(cd "$(dirname "$0")" && pwd)
TSV=$HERE/PICKS.tsv

[ -d "$DIR/ggml/src/ggml-cuda" ] || { echo "not a llama.cpp tree: $DIR" >&2; exit 2; }
cd "$DIR" || exit 2

n=0
while IFS=$'\t' read -r step sha pr subject surface applies status evidence; do
  case "$step" in step|'#'*|c*) continue;; esac
  # AUDIT27: status drift used to be silent (ADOPTABLE was invisible to both modes)
  case "$status" in TESTING|ADOPTABLE|ADOPTED|INERT|NEW|REJECTED|NA) ;;
    *) echo "unknown status '$status' at step $step" >&2; exit 5;; esac
  [ "$step" -le "$UPTO" ] || continue
  case "$MODE" in
    --all)   case "$status" in TESTING|ADOPTABLE|ADOPTED) ;; *) continue;; esac ;;
    --upto)  ;;
    *)       [ "$status" = "ADOPTED" ] || continue ;;
  esac
  p=$HERE/patches/$sha.patch
  [ -f "$p" ] || { echo "missing patch: $p"; exit 3; }
  git apply -p1 --exclude='ggml/src/ggml-cuda/mmq.cu' --exclude='ggml/src/ggml-cuda/moe_mmq.cu' "$p" \
    || { echo "FAILED to apply $sha ($pr)"; exit 4; }
  echo "applied  step=$step  $sha  #$pr  $subject"
  n=$((n+1))
done < "$TSV"
echo "done: $n patch(es) applied to $DIR"
