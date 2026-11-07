#!/bin/bash
set -u
B=/home/albus/strata166/gfx029-build

echo "=== 链接 ==="
docker run --rm -v $B:/out -w /out strata-gfx906:0.2.9-101 bash -lc '
cd /out
/opt/rocm/lib/llvm/bin/clang++ -O3 -DNDEBUG --offload-arch=gfx906 CMakeFiles/strata.dir/src/program/generate.cpp.o -o strata libstrata_engine.a libstrata_prefill.a libstrata_spec.a libstrata_engine.a libstrata_kernels.a libstrata_core.a libstrata_kernels_cpu.a ggml/src/libggml-cpu.a /opt/rocm/lib/libhipblas.so.3.7 /opt/rocm/lib/librocblas.so.5.7 libstrata_mmq.a libstrata_mmq_w4a4.a /opt/rocm/lib/libamdhip64.so.7.16.26323-0000000 /opt/rocm/lib/llvm/lib/clang/24/lib/linux/libclang_rt.builtins-x86_64.a /opt/rocm/lib/libamdhip64.so.7.16.26323-0000000 ggml/src/libggml-base.a -lm > /tmp/ld.log 2>&1
echo "LD_RC=$?"
tail -3 /tmp/ld.log
' 2>&1 | tail -6

echo
echo "=== 产物验证 ==="
ls -l $B/strata | awk '{print $5, $6, $7, $8}'
md5sum $B/strata
echo "--- 应有（各 >=1）：fatal GPU error / INJECT_FATAL / PLE 提限 ---"
printf "%-28s %s\n" "fatal GPU error" "$(strings $B/strata | grep -c 'fatal GPU error')"
printf "%-28s %s\n" "STRATA_INJECT_FATAL" "$(strings $B/strata | grep -c 'STRATA_INJECT_FATAL')"
printf "%-28s %s\n" "PLE raise-limit" "$(strings $B/strata | grep -c 'this program may lock only')"
echo "--- 应为 0：R66/R68 的四个 ---"
for k in STRATA_PF_GROUP_SCRATCH STRATA_PREFILL_ROUTED_STREAM STRATA_PF_HC_REGION STRATA_SERVE_STOP_BOUND; do
  printf "%-30s %s\n" "$k" "$(strings $B/strata | grep -c $k)"
done
echo "--- serve_stop_bound 符号 ---"
nm -C $B/strata 2>/dev/null | grep -c "serve_stop_bound"
