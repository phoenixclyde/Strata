set +e
D=/home/albus/strata166/gfx029
echo "===== gemm.cu: f16_inplace 的启用条件（f16_io_ 何时为真） ====="
sed -n '575,625p' "$D/src/prefill/gemm.cu"
echo
echo "===== 调用点 1180 的上下文（何时走 f16_inplace） ====="
sed -n '1165,1195p' "$D/src/prefill/gemm.cu"
