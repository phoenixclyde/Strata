set +e
D=/home/albus/strata166/gfx029
echo "===== [1] CMakeLists 840-880（rocBLAS / hipBLASLt / tuner 的门控） ====="
sed -n '840,880p' "$D/CMakeLists.txt"
echo
echo "===== [2] hipblaslt_tuning.hpp 的表名解析（arch-version） ====="
grep -n "arch\|version\|\.txt\|gfx" "$D/src/prefill/hipblaslt_tuning.hpp" | head -20
echo
echo "===== [3] rocblas_tuning.hpp 的表名与版本匹配规则 ====="
sed -n '1,80p' "$D/src/prefill/rocblas_tuning.hpp"
