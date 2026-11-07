set +e
D=/home/albus/strata166/gfx029
echo "===== [1] tuner 的两阶段（quick 筛选 + 精测）与 reps ====="
sed -n '150,250p' "$D/tools/hip/tune_rocblas.cpp"
