#!/bin/sh
# ci/isa_dump.sh -- disassemble one HIP translation unit the only safe way.
#
# W1045 incident (read this before changing anything here):
#   `llvm-objcopy --dump-section .hip_fatbin FILE` WITHOUT an output path
#   REWRITES FILE IN PLACE and removes the section. Run against the production
#   engine it turned 43,452,008 B into 43,425,632 B -- the running process kept
#   the old inode so service was fine, but the next restart would have loaded a
#   binary with no device code. Three rules follow, and this script enforces all
#   three: work on a copy, never point at /data/bin, always pass an output path.
#
# The other lesson (W1042/W1046): `llvm-objdump -d` on a host-wide executable
# prints only the x86 stub, and a whole-binary fatbin gives a handful of lines.
# Device code must come out of the .o for that TU, then through the bundler.
#
# usage: isa_dump.sh <path-to-.o|binary> [workdir]
#   exit 0 ok   |   2 refused   |   3 toolchain missing
set -eu

src=${1:?usage: isa_dump.sh <path-to-.o|binary> [workdir]}
work=${2:-/tmp/isa_dump.$$}
LLVM=${LLVM:-/opt/rocm/lib/llvm/bin}

case "$src" in
  /data/bin/*|*/data/bin/*)
    echo "REFUSED: '$src' is under /data/bin (production). Copy it first:" >&2
    echo "  cp $src /tmp/x.bin && $0 /tmp/x.bin" >&2
    exit 2 ;;
esac
[ -f "$src" ] || { echo "no such file: $src" >&2; exit 2; }
[ -x "$LLVM/llvm-objcopy" ] || { echo "no llvm toolchain at $LLVM" >&2; exit 3; }

mkdir -p "$work"
cp -f "$src" "$work/in.bin"          # rule 1: never touch the input
out="$work/fat.bin"

# rule 3: explicit output path (this is the W1045 bug if omitted)
if ! "$LLVM/llvm-objcopy" --dump-section .hip_fatbin="$out" "$work/in.bin" 2>"$work/objcopy.err"; then
  echo "no .hip_fatbin in $src -- this TU carries NO device code." >&2
  sed -n '1,3p' "$work/objcopy.err" >&2
  exit 2
fi
echo "fatbin=$(stat -c%s "$out") B"

targets=$("$LLVM/clang-offload-bundler" -list -type=o -input="$out" 2>/dev/null || true)
target=$(printf '%s\n' "$targets" | grep -m1 gfx906 || true)
if [ -z "$target" ]; then
  echo "no gfx906 bundle; targets were:" >&2
  printf '  %s\n' "$targets" | head -5 >&2
  exit 2
fi

"$LLVM/clang-offload-bundler" -type=o -unbundle -targets="$target" -input="$out" -output="$work/code.o"
"$LLVM/llvm-objdump" -d --mcpu=gfx906 "$work/code.o" > "$work/code.s"
echo "target=$target  disasm_lines=$(wc -l < "$work/code.s")  work=$work"

for op in v_dot4_i32_i8 v_dot8_i32_i4 v_dot2_f32_f16 v_mad_i32_i24 v_fmac_f32; do
  printf '  %-18s %s\n' "$op" "$(grep -c "$op" "$work/code.s" || true)"
done
