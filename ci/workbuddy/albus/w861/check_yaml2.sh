set +e
V20=/home/albus/strata166/data/w860_vega20
F=$V20/logic/vega20_Cijk_Ailk_Bjlk_HHS_BH.yaml
echo "=== size ==="; wc -l $F; du -h $F
echo "=== top 25 ==="; sed -n '1,25p' $F
echo "=== batching count ==="; grep -cE "^  - Batches:" $F; grep -c "Solutions:" $F
echo "=== total solutions (SolutionIndex) ==="; grep -c "SolutionIndex" $F
echo "=== problemtype block ==="; sed -n '/^  ProblemType:/,/^  Solutions:/p' $F | head -30
