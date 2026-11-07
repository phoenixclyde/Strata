#!/bin/bash
# W856 · hipBLASLt 支线 P0 第二轮：补齐 Python 依赖后，让 TensileCreateLibrary 真的跑一次 gfx906 codegen
# 依赖策略：跑 → 撞 ModuleNotFoundError: X → pip install X 到 /out/pylib → 重跑（最多 8 轮）
set -u
SRC=/home/albus/strata166/rocm-libs
IMG=strata-gfx906:0.2.9-101
OUT=/home/albus/strata166/data/w856_hblt_p0
LOG=$OUT/p0b_$(date +%H%M%S).log
mkdir -p "$OUT"; : > "$LOG"
exec > >(tee -a "$LOG") 2>&1
hl(){ printf '\n== %s\n' "$1"; }

Y=/src/projects/hipblaslt/tensilelite/tensilelite/Tests/unit/characterization/_codegen/data/gfx1100/SB.yaml
hl "1 依赖补齐 + codegen（gfx906, yaml=SB.yaml）"
docker run --rm --entrypoint bash -v "$SRC":/src:ro -v "$OUT":/out "$IMG" -lc "
set -u
export PYTHONPATH=/out/pylib:/src/projects/hipblaslt/tensilelite
cd /src/projects/hipblaslt/tensilelite
mkdir -p /out/gen /out/pylib
for i in \$(seq 1 8); do
  echo \"--- attempt \$i ---\"
  out=\$(python3 tensilelite/bin/TensileCreateLibrary --architecture=gfx906 --logic=$Y \
        --output-path=/out/gen --code-object-version=5 --library-format=yaml 2>&1)
  echo \"\$out\" | tail -12
  mod=\$(echo \"\$out\" | grep -o \"No module named '[^']*'\" | head -1 | sed \"s/No module named '//;s/'//;s/\\..*//\")
  if [ -n \"\$mod\" ]; then
    echo \"  -> installing \$mod\"
    python3 -m pip install --target /out/pylib --no-cache-dir -q \"\$mod\" 2>&1 | tail -2
    continue
  fi
  break
done
echo '--- 产物 ---'
find /out/gen -type f 2>/dev/null | head -12
" 2>&1 | tail -55

hl "2 判定"
if grep -qiE "requires gfx90a\+|amdhsa_accum_offset|unknown directive" "$LOG"; then
  echo "WALL —— 汇编阶段撞 gfx90a+ 指令"
elif find "$OUT/gen" \( -name '*.hsaco' -o -name '*.co' \) 2>/dev/null | grep -q .; then
  echo "PASS —— 有 .hsaco 产物"
elif find "$OUT/gen" -name '*.s' 2>/dev/null | grep -q .; then
  echo "PARTIAL —— 生成了 .s 但未汇编成 .hsaco（看上面汇编器报错）"
else
  echo "BLOCK —— 仍未产出（见上）"
fi
echo "日志: $LOG"
