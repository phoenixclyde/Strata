echo "=== 0. production right now ==="
date +%H:%M:%S
docker ps --format '{{.Names}} {{.Status}}' | grep -Ei 'strata|w828' || echo "NO CONTAINER"
curl -s --max-time 4 http://127.0.0.1:8090/health | head -c 120; echo
echo
echo "=== 1. is the old tree a git checkout? ==="
for d in /home/albus/strata166/src0271 /home/albus/strata166/src028 /home/albus/strata166/src; do
  printf '  %-40s ' "$d"
  if [ -d "$d/.git" ]; then echo "git=yes"; else echo "git=no"; fi
done
echo "--- src0271 git ---"
git -C /home/albus/strata166/src0271 log --oneline -5 2>&1 | head -6
git -C /home/albus/strata166/src0271 status --short 2>&1 | head -12
echo "--- src0271 diff vs HEAD (stat) ---"
git -C /home/albus/strata166/src0271 diff --stat HEAD 2>&1 | tail -12
echo
echo "=== 2. patch material on disk ==="
ls -la /home/albus/strata166 | head -30
echo "--- *.patch / patches dirs ---"
find /home/albus/strata166 -maxdepth 3 \( -name '*.patch' -o -name '*.diff' -o -name 'patches' \) 2>/dev/null | head -20
echo
echo "=== 3. the two source trees at a glance ==="
du -sh /home/albus/strata166/src0271 /home/albus/strata166/src028 2>/dev/null
ls /home/albus/strata166/src0271 | head -20
