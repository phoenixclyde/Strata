#!/bin/bash
set -u
C=strata166-407
echo "=== 1) 源码树里 dot4 / dot8 的使用（rebase 后的 0.2.10） ==="
cd /home/albus/strata166/pr/strata-fork || exit 1
for p in "ggml_cuda_dp4a" "__dp4a" "sdot4" "sdot8" "udot8" "__builtin_amdgcn_sdot8" "v_dot8" "dot8"; do
  printf "%-30s strata=%-4s llama=%-4s\n" "$p" \
    "$(grep -rl "$p" --include=*.cu --include=*.cuh --include=*.h --include=*.hpp src/ include/ 2>/dev/null | wc -l)" \
    "$(grep -rl "$p" --include=*.cu --include=*.cuh --include=*.h --include=*.hpp /home/albus/strata166/llama.cpp/ggml/src/ggml-cuda/ 2>/dev/null | wc -l)"
done

echo
echo "=== 2) 当前生产引擎 0.1.56 的 dot 指令计数（重跑 W909 的口径） ==="
docker exec $C sh -lc 'cd /tmp && rm -rf w939cos && llvm-objcopy --dump-section=.hip_fatbin=fat156.bin /proc/14/exe 2>/dev/null; ls -l fat156.bin | awk "{print \$5}"; python3 carve_elf.py fat156.bin w939cos 2>&1 | tail -1; for f in w939cos/*.elf; do llvm-objdump -d $f 2>/dev/null; done > prod156.txt; echo "--- 指令构成 ---"; for i in v_dot4_i32_i8 v_dot4_u32_u8 v_dot8_i32_i4 v_dot8_u32_u4 v_fmac_f32 v_mul_lo_u32; do printf "%-18s %s\n" "$i" "$(grep -c "$i" prod156.txt)"; done; echo -n "总静态指令 "; grep -cE "^\s+[a-z]" prod156.txt; echo -n "内核数 "; grep -c s_endpgm prod156.txt'
