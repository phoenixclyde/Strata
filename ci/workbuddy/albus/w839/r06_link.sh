#!/bin/bash
# W839-06 链接面诊断
S=/home/albus/strata166/src028
B=$S/build-028r
echo "=== build-028r 顶层可执行 ==="
ls -la $B/strata* 2>/dev/null | cut -c1-95
file $B/strata 2>/dev/null | cut -c1-120

echo "=== 二进制里找符号 ==="
for sym in gfx_arch_is_gfx906 apply_arch_defaults arch_default_env; do
  printf '  %-24s %s\n' "$sym" "$(nm -C $B/strata 2>/dev/null | grep -c "$sym")"
done
echo "--- 对象里找符号 ---"
for o in $(find $B -name 'arch_defaults*.o' | head -3); do
  echo "[$o] $(nm -C $o 2>/dev/null | grep -c 'gfx_arch_is_gfx906')"
done

echo "=== 有多少个 arch_defaults 对象（可能被编多次） ==="
find $B -name 'arch_defaults*.o' | sed "s#$B/##"
echo "=== 静态库时间戳 ==="
find $B -name 'libstrata*.a' -printf '%TY-%Tm-%Td %TH:%TM  %p\n' 2>/dev/null | head -6

echo "=== ninja 认为谁产出 strata ==="
grep -n 'build strata' $B/build.ninja | head -3
echo "=== 链接命令里的对象是库还是散对象 ==="
grep -A3 'build strata:' $B/build.ninja | head -6
