set +e
echo "=== date ==="; date -u +%FT%TZ
echo "=== containers ==="
docker ps --format '{{.Names}} {{.Status}} {{.Image}}' | head
echo "=== strata status ==="
docker exec strata166-407 strata status 2>&1 | head -20
echo "=== hipblaslt tree ==="
ls -d /home/albus/hblt* /home/albus/*/hipBLASLt 2>/dev/null
find /home/albus -maxdepth 3 -name "tensilelite-client" -type f 2>/dev/null
echo "=== mapping ==="
find /home/albus -maxdepth 6 -name "*Mapping.dat" 2>/dev/null | head
echo "=== build dirs ==="
ls -dt /home/albus/*/ 2>/dev/null | head -12
echo "=== nproc/mem ==="
nproc; free -g | head -2
