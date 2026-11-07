set +e
S=/home/albus/strata166/rocm-libs
V20=/home/albus/strata166/data/w860_vega20
W858=/home/albus/strata166/data/w858_hblt
echo "=== logic yaml ==="
ls -la $V20/logic/
echo "--- solution count (lists in yaml) ---"
grep -c "^- Solution" $V20/logic/vega20_Cijk_Ailk_Bjlk_HHS_BH.yaml 2>/dev/null
grep -oE "SolutionIndex: [0-9]+" $V20/logic/vega20_Cijk_Ailk_Bjlk_HHS_BH.yaml | wc -l
head -30 $V20/logic/vega20_Cijk_Ailk_Bjlk_HHS_BH.yaml
echo "=== pylib has joblib? ==="
ls $W858/pylib | head -30
echo "=== TCL help ==="
docker run --rm -v $S:/src -v $W858:/g858 strata-gfx906:0.2.9-101 bash -lc '
TL=/src/projects/hipblaslt/tensilelite
export PYTHONPATH=/g858/pylib:/g858/rocisa-install:$TL
cd /tmp && python3 -m Tensile.TensileCreateLibrary --help 2>&1 | head -50
' 2>&1 | tail -55
