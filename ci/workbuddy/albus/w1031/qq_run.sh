#!/bin/bash
# qq_run.sh — 用 tools/quant_quality.py 做 001 vs K10 的 teacher-forced top-1 / KL 对照。
# 生产容器先停（独占 GPU），跑完（无论成败）自动把生产拉回来。
#   001 = /data/bin/strata-0.1.57-001（在产基线）
#   K10 = /data/bin/strata-0.1.57-010（0.9.0 树 + mmq 头@4c1004c，含 #29953/#30168/#30553）
set -uo pipefail
IMG=strata-gfx906:0.2.11-101
DATA=/home/albus/strata166/data
CFG=$DATA/strata-huihui-ud-iq4_xs.json

restore() {
  echo "=== restore production container"
  docker start strata166-407 >/dev/null 2>&1
  for i in $(seq 1 40); do
    h=$(curl -s -m 4 localhost:8090/health || true)
    case "$h" in *'"ok"'*) echo "production healthy after ${i}0s"; return;; esac
    sleep 10
  done
  echo "!! production did not come back"
}
trap restore EXIT

echo "=== 0. stop production"
docker stop -t 30 strata166-407 >/dev/null 2>&1
sleep 5
n=$(ps -eo args | grep -c '^/data/bin/strata-0\.1')
used=$(rocm-smi --showmeminfo vram 2>/dev/null | grep -m1 "Used Memory (B)" | grep -o '[0-9]*$')
echo "engines=$n vram_used=${used:-?}"
if [ "$n" != "0" ] || { [ -n "${used:-}" ] && [ "$used" -gt 2000000000 ]; }; then
  echo "REFUSE: GPU still busy"; exit 10
fi

echo "=== 1. configs"
python3 - "$CFG" "$DATA" <<'PY'
import json, sys
src, data = sys.argv[1], sys.argv[2]
d = json.load(open(src))
for tag, exe in (("001", "strata-0.1.57-001"), ("k10", "strata-0.1.57-010")):
    e = dict(d); e["exe"] = "/data/bin/" + exe
    json.dump(e, open("%s/qq_%s.json" % (data, tag), "w"), indent=1)
    print("wrote", "%s/qq_%s.json" % (data, tag), "exe=", e["exe"])
PY

run_one() {  # run_one <tag>
  local tag=$1
  echo "=== run $tag  $(date +%H:%M:%S)"
  docker run --rm --name "qq_$tag" --device=/dev/kfd --device=/dev/dri \
    --ulimit memlock=-1:-1 --security-opt label=disable \
    -v /models:/models:ro -v "$DATA":/data "$IMG" bash -lc "
python3 /src/tools/quant_quality.py run --config /data/qq_$tag.json --out /data/qq_$tag.tsv --gpu-experts 2>&1 | tail -8"
  echo "=== run $tag rc=$?  $(date +%H:%M:%S)"
}

run_one 001
run_one k10

echo "=== 3. compare (REF=001, RUN=k10)"
docker run --rm --name qq_cmp -v "$DATA":/data "$IMG" bash -lc "
python3 /src/tools/quant_quality.py compare /data/qq_001.tsv /data/qq_k10.tsv 2>&1 | tail -20"
