set +e
O=/home/albus/strata166/tuner-build-r101
D=/home/albus/strata166/gfx029
echo "===== [1] tuner 默认形状（引擎的 NK 列表） ====="
sed -n '/if (!o.explicit_shapes)/,/^    }/p' "$D/tools/hip/tune_rocblas.cpp" | head -16
echo
echo "===== [2] tuner help + 单 case 计时（gfx906, rocBLAS 5.7） ====="
time docker run --rm --device /dev/kfd --device /dev/dri --group-add video \
  --security-opt label=disable -v "$O":/tb:ro -v /home/albus/strata166/data:/data \
  strata-gfx906:0.2.9r1 bash -lc '
/tb/tune_rocblas 2>&1 | head -3
echo "--- 单 case 试跑:"
time /tb/tune_rocblas --case 256,10240,2560,10240 --min-gain 1.5 --tuning-out /data/w851_one.txt 2>&1 | tail -4
echo "--- 输出表:"
cat /data/w851_one.txt
'
