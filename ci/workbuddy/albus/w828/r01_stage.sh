set -e
cd /home/albus/strata166
rm -rf dl/up028
mkdir -p dl/up028
tar xzf dl/up028.tgz -C dl/up028
echo "files: $(find dl/up028 -type f | wc -l)"

# rebuild src028 from src0271 + the 148 changed files (idempotent)
rm -rf src028
rsync -a --exclude build-0271 --exclude build-0271_out src0271/ src028/
cp -a dl/up028/. src028/
grep -n 'project(strata VERSION' src028/CMakeLists.txt

# every file the compare API lists must differ-or-match; report the count only
echo "missing from src028:"
cd dl/up028
find . -type f | while read f; do [ -f "/home/albus/strata166/src028/$f" ] || echo "  $f"; done
cd /home/albus/strata166
df -h / | tail -1
docker ps --format '{{.Names}}' | grep -c strata166 || true
