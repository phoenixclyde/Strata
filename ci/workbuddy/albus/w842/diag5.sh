set +e
S=/home/albus/strata166/src028/serve/server.py
echo "=== engine_binary() ==="
sed -n '3044,3062p' "$S"
echo
echo "=== _component_exe() ==="
sed -n '8680,8700p' "$S"
