#!/bin/bash
# probe_tensilelite.sh — P0 判定：TensileLite 能不能为 gfx906 生成并汇编出**一个** kernel
#
# 判据（写死在最后）：
#   PASS  = 产出 .hsaco（或 .co）且没有 ".amdhsa_accum_offset ... requires gfx90a+" 之类错误
#   WALL  = 汇编阶段撞 gfx90a+ directive  ⇒ 必须改 asm 生成器，成本从「天」跳到「周」
#   BLOCK = 连 codegen 都跑不起来（缺 logic / 缺 Python 依赖 / 入口找不到）
#
# 用法：bash probe_tensilelite.sh [源码目录]
#  默认源码目录 /home/albus/strata166/rocm-libs
#  改到自己的目录也可以：bash probe_tensilelite.sh /path/to/rocm-libs
set -u
SRC=${1:-/home/albus/strata166/rocm-libs}
TL=$SRC/projects/hipblaslt/tensilelite
OUT=/home/albus/strata166/tl_probe_out
IMG=strata-gfx906:0.2.9-101      # ROCm 10.1（rocisa 7.16）
LOG=$OUT/probe_$(date +%H%M%S).log

hl(){ printf '\n\033[1m== %s\033[0m\n' "$1"; }

mkdir -p "$OUT"
: > "$LOG"
exec > >(tee -a "$LOG") 2>&1

hl "0 前置检查"
[ -d "$TL" ] || { echo "BLOCK: 源码目录不存在：$TL"; echo "  先跑：git clone --depth 1 --filter=blob:none --sparse <rocm-libraries> && git sparse-checkout set projects/hipblaslt/tensilelite"; exit 2; }
echo "  源码: $TL"
echo "  文件数: $(find "$TL" -type f | wc -l)"
echo "  镜像: $IMG"

hl "1 确认上游确实排除了 gfx906（改之前先留证）"
CM=$TL/cmake/tensilelite_supported_architectures.cmake
if [ -f "$CM" ]; then
  echo "  $CM 里 gfx906 命中: $(grep -c gfx906 "$CM")"
  grep -n "SUPPORTED_ARCHITECTURES" -A 8 "$CM" | head -12
else
  echo "  WARN: 找不到 $CM"
fi
echo "  对照：Architectures.py 里的 vega20 映射"
grep -rn '"gfx906"' "$TL"/tensilelite/Common/Architectures.py 2>/dev/null | head -3

hl "2 打白名单补丁（幂等）"
if grep -q '"gfx906"' "$CM" 2>/dev/null; then
  echo "  已含 gfx906，跳过"
else
  python3 - "$CM" <<'PY'
import io, sys, re
p = sys.argv[1]
s = io.open(p, encoding="utf-8").read()
# 在 SUPPORTED_ARCHITECTURES 的 set(...) 里、第一个 "gfx 之前插入
m = re.search(r'set\(SUPPORTED_ARCHITECTURES\b(.*?)\)', s, re.S)
if not m:
    print("  FAIL: 找不到 set(SUPPORTED_ARCHITECTURES ...)"); sys.exit(1)
body = m.group(1)
if '"gfx906"' not in body:
    body2 = '\n    "gfx906"' + body
    s = s[:m.start(1)] + body2 + s[m.end(1):]
# BASE_ARCHITECTURES 的 else 分支同样加一条
m2 = re.search(r'set\(BASE_ARCHITECTURES\b(.*?)\)', s, re.S)
if m2 and '"gfx906"' not in m2.group(1):
    s = s[:m2.start(1)] + '\n        "gfx906"' + s[m2.end(1):]
io.open(p, "w", encoding="utf-8").write(s)
print("  patched:", p)
PY
  echo "  改后 gfx906 命中: $(grep -c gfx906 "$CM")"
fi

hl "3 找 codegen 入口"
for c in \
  "$TL/tensilelite/Tensile/bin/TensileCreateLibrary" \
  "$TL/Tensile/bin/TensileCreateLibrary" \
  "$TL/tensilelite/Tensile/TensileCreateLibrary.py" ; do
  [ -e "$c" ] && echo "  found: $c"
done
python3 -c "import sys;sys.path.insert(0,'$TL');import tensilelite" 2>&1 | head -3

hl "4 在镜像里跑最小 codegen（1 个 shape，gfx906）"
# 用镜像里的 rocisa（.so）+ 宿主源码；只生成、不跑 kernel
docker run --rm --entrypoint bash -v "$SRC":/src:ro -v "$OUT":/out "$IMG" -lc '
set -u
cd /src/projects/hipblaslt/tensilelite 2>/dev/null || { echo "BLOCK: 镜像内看不到源码"; exit 3; }
PYBIN=$(command -v python3)
echo "  python: $($PYBIN -V 2>&1)"
$PYBIN - <<PY 2>&1 | tail -40
import sys, os
sys.path.insert(0, "/src/projects/hipblaslt/tensilelite")
try:
    import rocisa
    print("  rocisa import OK:", getattr(rocisa, "__file__", "?"))
except Exception as e:
    print("  rocisa import FAIL:", type(e).__name__, e)
try:
    from tensilelite.Common.Architectures import architectureMap
    print("  architectureMap has gfx906:", "gfx906" in architectureMap, "->", architectureMap.get("gfx906"))
except Exception as e:
    print("  Architectures import FAIL:", type(e).__name__, e)
PY
echo "--- 尝试 TensileCreateLibrary --help（只看入口活不活）"
for e in tensilelite/Tensile/bin/TensileCreateLibrary Tensile/bin/TensileCreateLibrary; do
  [ -f "$e" ] || continue
  echo "  entry: $e"
  $PYBIN "$e" --help 2>&1 | head -12
  break
done
' 2>&1 | tail -50

hl "5 判定"
if grep -qiE "requires gfx90a\+|amdhsa_accum_offset|unknown directive" "$LOG"; then
  echo "WALL —— 汇编阶段撞 gfx90a+ 指令：TensileLite 的 asm 生成器依赖 MFMA 累加器布局。"
  echo "        下一步不是调参数，是改 kernel 模板（见 PLAN.md 第 5 步）。"
elif grep -qiE "\.hsaco|\.co\b|generated" "$LOG"; then
  echo "PASS(部分) —— 有生成产物，仍需确认它能否被汇编并在 gfx906 上加载。"
else
  echo "BLOCK —— codegen 没跑起来（缺 logic / 缺依赖 / 入口不对）。把上面第 4 段的报错原文留下来。"
fi
echo
echo "完整日志: $LOG"
