#!/usr/bin/env bash
# [W863 R33] Ask the compiler what the real kernels cost: VGPRs, SGPRs, LDS per block, spills.
#
# Why: occupancy on gfx9 is arithmetic, not vibes. Each SIMD has 256 VGPRs; waves per SIMD is
# floor(256 / roundup(vgpr, granule)). LDS is 64 KiB per CU. If the HC kernels sit just above a
# register granule, one wave per SIMD is left on the table for a two-register change.
set -u
REPO=/home/albus/strata166/pr/strata-fork
OUT=/home/albus/strata166/ci/state/vgpr
mkdir -p "$OUT"

echo "=== 1. the exact compile command ninja uses for this TU ==="
docker run --rm -v "$REPO":/src -v /home/albus/strata166/gfx029-build:/out -w /out \
  strata-gfx906:0.2.9-101 \
  bash -c 'ninja -t commands 2>/dev/null | grep -E "fused_gr\.cu\.o" | grep -v llvm-ar | grep -v bench | grep -- " -c " | tail -1' \
  > "$OUT/cmd.txt" 2>&1
wc -c < "$OUT/cmd.txt"
head -c 300 "$OUT/cmd.txt"; echo; echo "..."

echo
echo "=== 2. re-emit assembly only (-S): VGPR/SGPR/LDS are in the asm metadata ==="
# Same flags, only the output changes, so the numbers belong to the shipped kernel.
docker run --rm -v "$REPO":/src -v /home/albus/strata166/gfx029-build:/out -v "$OUT":/work \
  -w /out strata-gfx906:0.2.9-101 \
  bash -c 'set -e
    CMD=$(cat /work/cmd.txt)
    # swap "-o <obj>" for "-S -o /work/fused_gr.s"
    NEW=$(printf "%s" "$CMD" | sed -E "s#-o [^ ]*fused_gr\.cu\.o#--cuda-device-only -S -o /work/fused_gr.s#")
    echo "$NEW" | head -c 200; echo " ..."
    eval "$NEW" 2>&1 | tail -5
    ls -l /work/fused_gr.s' 2>&1 | tail -8

echo
echo "=== 3. the numbers ==="
python3 - <<'PY'
import re, os
p = "/home/albus/strata166/ci/state/vgpr/fused_gr.s"
if not os.path.exists(p):
    print("no asm produced"); raise SystemExit
txt = open(p, errors="replace").read()

# clang emits per-kernel attributes in the .amdgpu_metadata yaml block
blocks = re.split(r"\n\s*---\s*\n", txt)
rows = []
for b in blocks:
    name = re.search(r"Name:\s+(\S+)", b)
    vg = re.search(r"vgpr_count:\s+(\d+)", b)
    sg = re.search(r"sgpr_count:\s+(\d+)", b)
    grp = re.search(r"group_segment_fixed_size:\s+(\d+)", b)
    priv = re.search(r"private_segment_fixed_size:\s+(\d+)", b)
    if name and vg:
        rows.append((name.group(1), int(vg.group(1)), int(sg.group(1)) if sg else -1,
                     int(grp.group(1)) if grp else -1, int(priv.group(1)) if priv else -1))

def waves(vgpr):
    # gfx9: 256 VGPRs per SIMD, allocation granule 4
    g = ((vgpr + 3) // 4) * 4
    return max(1, 256 // g)

print("%-46s %6s %6s %9s %9s %7s" % ("kernel", "vgpr", "sgpr", "lds/blk", "priv/blk", "waves/SIMD"))
for n, vg, sg, grp, priv in sorted(rows, key=lambda r: r[0]):
    if "gr_" in n or "q8" in n.lower():
        print("%-46s %6d %6d %9d %9d %7d" % (n[:46], vg, sg, grp, priv, waves(vg)))
print()
print("total kernels with metadata: %d  (filtered to gr_*/q8*)" % len(rows))
lds = [r[3] for r in rows if r[3] > 0]
if lds:
    print("max LDS per block in this TU: %d B -> at 65536 B/CU that is %d blocks/CU"
          % (max(lds), 65536 // max(lds)))
PY
