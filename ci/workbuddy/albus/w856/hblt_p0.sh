#!/bin/bash
# W856 · hipBLASLt 支线 P0：TensileLite 能不能为 gfx906 生成并汇编出一个 kernel
# 判据（PLAN.md §3 写死）：
#   PASS  = 生成 .s 且 amdclang++ 汇编成 .hsaco
#   WALL  = 汇编阶段撞 .amdhsa_accum_offset / unknown directive（必须改 asm 生成器）
#   BLOCK = codegen 起不来（缺 logic / 缺 Python 依赖 / 入口参数不对）
# 本脚本只用 CPU，不碰生产、不占 GPU。
set -u
SRC=/home/albus/strata166/rocm-libs
TL=$SRC/projects/hipblaslt/tensilelite
IMG=strata-gfx906:0.2.9-101
OUT=/home/albus/strata166/data/w856_hblt_p0
LOG=$OUT/p0_$(date +%H%M%S).log
mkdir -p "$OUT"; : > "$LOG"
exec > >(tee -a "$LOG") 2>&1
hl(){ printf '\n== %s\n' "$1"; }

hl "0 前置"
echo "  tensilelite: $(find "$TL" -type f | wc -l) files"
echo "  yaml 候选:"; find "$TL/tensilelite/Tests/unit/characterization/_codegen/data" -name '*.yaml' | head -6

hl "1 入口与 CLI（在镜像里）"
docker run --rm --entrypoint bash -v "$SRC":/src:ro -v "$OUT":/out "$IMG" -lc '
set -u
export PYTHONPATH=/src/projects/hipblaslt/tensilelite
cd /src/projects/hipblaslt/tensilelite
echo "  python: $(python3 -V 2>&1)"
echo "  amdclang++: $(command -v amdclang++ || echo MISSING)"
python3 - <<PY
import sys
sys.path.insert(0,"/src/projects/hipblaslt/tensilelite")
for mod in ("rocisa","tensilelite","tensilelite.Tensile","tensilelite.TensileCreateLibrary.Run"):
    try:
        __import__(mod); print("  import OK:", mod)
    except Exception as e:
        print("  import FAIL:", mod, type(e).__name__, str(e)[:120])
try:
    from tensilelite.Common.Architectures import architectureMap
    print("  arch map gfx906 =", architectureMap.get("gfx906"))
except Exception as e:
    print("  arch map FAIL:", type(e).__name__, str(e)[:120])
import rocisa
print("  rocisa file:", getattr(rocisa,"__file__","?"))
try:
    isa = rocisa.rocIsa.getInstance()
    isa.setKernel(isa.getKernel("gfx906", "f16", 2, 2))
    print("  gfx906 ISA: MFMA =", isa.isMFMA(), "| WMMA =", getattr(isa,"isWMMA",lambda:None)())
except Exception as e:
    print("  ISA probe FAIL:", type(e).__name__, str(e)[:160])
PY
echo "--- TensileCreateLibrary --help ---"
python3 tensilelite/bin/TensileCreateLibrary --help 2>&1 | head -30
' 2>&1 | tail -45

hl "2 最小 codegen 尝试（gfx906 + 一个 gfx1100 的 codegen 用 yaml）"
Y=$(find "$TL/tensilelite/Tests/unit/characterization/_codegen/data/gfx1100" -name 'SB.yaml' | head -1)
echo "  yaml: $Y"
docker run --rm --entrypoint bash -v "$SRC":/src:ro -v "$OUT":/out "$IMG" -lc "
set -u
export PYTHONPATH=/src/projects/hipblaslt/tensilelite
cd /src/projects/hipblaslt/tensilelite
mkdir -p /out/gen
python3 tensilelite/bin/TensileCreateLibrary --architecture=gfx906 --logic=/src/${Y#/src/} \
   --output-path=/out/gen --code-object-version=5 --library-format=yaml 2>&1 | tail -40
echo '--- 产物 ---'; find /out/gen -type f | head -10
" 2>&1 | tail -50

hl "3 判定"
if grep -qiE "requires gfx90a\+|amdhsa_accum_offset|unknown directive" "$LOG"; then
  echo "WALL —— 汇编阶段撞 gfx90a+ 指令（改 asm 生成器，按周计）"
elif find "$OUT" -name '*.hsaco' -o -name '*.co' | grep -q .; then
  echo "PASS —— 有 .hsaco 产物（仍要 P1 的 API 对拍才算数）"
elif grep -qiE "no logic|not found|Unsupported GPU target" "$LOG"; then
  echo "BLOCK —— 缺 vega20 logic / 目标被白名单拒（本轮已看到具体行，见上）"
else
  echo "BLOCK —— codegen 未产出（见上面最后 20 行）"
fi
echo "日志: $LOG"
