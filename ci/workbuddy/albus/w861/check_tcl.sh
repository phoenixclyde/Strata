set +e
C=strata166-407
S=/home/albus/strata166/rocm-libs
echo "=== TCL help ==="
docker run --rm -v $S:/src strata-gfx906:0.2.9-101 bash -lc '
export PYTHONPATH=/src/projects/hipblaslt/tensilelite
python3 -m Tensile.TensileCreateLibrary --help 2>&1 | head -40
' 2>&1 | tail -45
echo "=== find vega20 logic yaml ==="
find /home/albus -name "vega20_Cijk_Ailk_Bjlk_HHS_BH.yaml" 2>/dev/null | head
find $S -name "vega20*HHS*" 2>/dev/null | head
echo "=== gen15 tree ==="
ls /home/albus/strata166/data/w859_hblt/gen15/ 2>/dev/null
find /home/albus/strata166/data/w859_hblt/gen15 -maxdepth 2 -type f 2>/dev/null | head -20
