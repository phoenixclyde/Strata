set +e
docker run --rm --entrypoint bash strata-gfx906:0.2.9t2 -lc '
B=/opt/rocm/core-7.14/share/hipblaslt/tensilelite
echo "===== 目录结构（两层） ====="
find $B -maxdepth 2 | head -30
echo
echo "===== Tensile 目录里是什么 ====="
ls -la $B/Tensile 2>/dev/null | head -14
echo
echo "===== rocisa 目录 ====="
ls $B/rocisa 2>/dev/null | head -10
'
