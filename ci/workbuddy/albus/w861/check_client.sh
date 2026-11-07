set +e
D=/home/albus/strata166/data
echo "=== client build logs ==="
for f in $D/w860_client_build.log $D/w860_client_build2.log; do echo "--- $f"; tail -25 "$f" 2>/dev/null; done
echo "=== w859_hblt dir ==="
ls -la $D/w859_hblt 2>/dev/null | head -20
echo "=== build dir ==="
ls $D/w859_hblt/build 2>/dev/null | head -20
echo "=== client target exists? ==="
ls $D/w859_hblt/build/projects/hipblaslt/tensilelite/client/ 2>/dev/null | head
echo "=== host python ==="
python3 -V; pip3 --version 2>&1 | head -1
