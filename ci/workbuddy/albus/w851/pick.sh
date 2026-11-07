set +e
D=/home/albus/strata166/gfx029
echo "===== rocblas_tuning.hpp 的 Pick（表行如何映射到 T） ====="
sed -n '90,175p' "$D/src/prefill/rocblas_tuning.hpp"
