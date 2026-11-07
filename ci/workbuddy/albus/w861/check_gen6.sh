set +e
D=/home/albus/strata166/data
echo "=== gen6 files ==="
ls -la $D/w858_hblt/gen6/
echo "=== gen6 mapping head ==="
head -c 200 $D/w858_hblt/gen6/TensileLiteLibrary_lazy_gfx906_Mapping.dat | xxd | head -8
echo "=== gen5/gen4 mapping? ==="
ls -la $D/w858_hblt/gen5/ $D/w858_hblt/gen4/ 2>/dev/null | head -30
echo "=== cfg_client2 full ==="
cat $D/w859_hblt/cfg_client2.log
echo "=== gen15/gen16 dirs ==="
ls -d $D/w859_hblt/gen1* $D/w859_hblt/gen* 2>/dev/null
echo "=== newest gen source library ==="
find $D/w859_hblt -path "*library/gfx906*" -name "*.hsaco" 2>/dev/null | head -5
find $D -name "TensileLibrary.yaml" 2>/dev/null | head -5
