set +e
D=/home/albus/strata166/data/w858_hblt
echo "=== top ==="; ls -la $D | head -30
echo "=== gen dirs sizes ==="; du -sh $D/* 2>/dev/null | sort -k2
echo "=== gen6 tree ==="; find $D/gen6 -maxdepth 3 | head -40
echo "=== all hsaco ==="; find $D -name "*.hsaco" -o -name "*.co" 2>/dev/null | head -20
echo "=== all yaml lazy ==="; find $D -name "TensileLibrary*" 2>/dev/null | head -20
echo "=== client ==="; find / -maxdepth 6 -name "tensilelite-client" -type f 2>/dev/null | head
echo "=== invoke ==="; which invoke; python3 -c "import invoke,sys;print(invoke.__version__)" 2>&1 | head -3
