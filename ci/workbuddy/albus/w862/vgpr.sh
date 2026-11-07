#!/bin/bash
# 读 native_mmvq 各 kernel 的 VGPR / LDS 占用，算每 CU 能驻留多少 wave。
set -u
R=/home/albus/strata166/pr/strata-fork
O=/home/albus/w862_vg
rm -rf "$O"; mkdir -p "$O"; cd "$O" || exit 1
export PATH=/opt/rocm/bin:/opt/rocm/llvm/bin:$PATH
hipcc --offload-arch=gfx906 -O3 -std=c++17 \
  -DSTRATA_HIP_GFX906=1 -DSTRATA_VERIFY_MAX_T=8 -D__HIP_PLATFORM_AMD__ \
  -I"$R/include" -I"$R/src" -I"$R/src/kernels/cuda" -I"$R/include/strata/hip_compat" \
  -c "$R/src/kernels/cuda/native_mmvq.cu" -o "$O/nm.o" --save-temps > "$O/cc.log" 2>&1
echo "rc=$?"
tail -3 "$O/cc.log"
S=$(ls "$O"/*.s 2>/dev/null | head -1)
echo "asm=$S"
if [ -n "$S" ]; then
  python3 - "$S" <<'PY'
import re, sys
txt = open(sys.argv[1], errors='ignore').read()
# 每个 .amdhsa_kernel 段：名字 + vgpr_count + sgpr_count + lds
blocks = re.split(r'\.amdhsa_kernel\s+', txt)
rows = []
for b in blocks[1:]:
    name = b.split('\n', 1)[0].strip()
    def g(k):
        m = re.search(r'\.' + k + r'\s+(\d+)', b)
        return int(m.group(1)) if m else -1
    rows.append((name, g('vgpr_count'), g('sgpr_count'), g('group_segment_fixed_size')))
want = [r for r in rows if 'wave_kernel' in r[0]]
print("=== wave kernels ===")
for n, v, s, l in want:
    if v > 0:
        # gfx906: 65536 VGPR / CU, 每 wave 64 lane
        waves = 65536 // (v * 64) if v else 0
        blocks = min(10, waves // 4)
        print("%-70s vgpr=%-4d sgpr=%-3d lds=%-5d -> waves/CU=%-3d blocks(4w)/CU=%d" % (n[:70], v, s, l, waves, blocks))
print("=== 全部 kernel 数 ===", len(rows))
PY
fi
