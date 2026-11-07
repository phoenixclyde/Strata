set +e
D=/home/albus/strata166/data
echo "=== gen6 ls ==="
ls -la $D/w858_hblt/gen6/ 2>/dev/null
echo "=== gen6 md5 ==="
md5sum $D/w858_hblt/gen6/*.dat $D/w858_hblt/gen6/*.hsaco 2>/dev/null
echo "=== rocm-libs/shared ==="
ls /home/albus/strata166/rocm-libs/shared/ | head -20
echo "=== mxdatagenerator? ==="
ls -d /home/albus/strata166/rocm-libs/shared/mxdatagenerator 2>&1
echo "=== TensileCreateLibrary help (mapping opts) ==="
docker run --rm -v /home/albus/strata166/rocm-libs:/src strata-gfx906:0.2.9-101 bash -lc '
export PYTHONPATH=/src/projects/hipblaslt/tensilelite
python3 -m Tensile.TensileCreateLibrary --help 2>&1 | grep -i -E "mapping|library-format|lazy|separate" | head -20
' 2>&1 | tail -25
