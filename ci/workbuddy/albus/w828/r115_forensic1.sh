set -u
DL=/home/albus/strata166/dl
mkdir -p "$DL"
cd "$DL" || exit 1
if [ ! -s v0271.tgz ]; then
  echo "downloading v0.2.7.1 ..."
  timeout 600 curl -sSL -o v0271.tgz https://codeload.github.com/Niko1221/Strata/tar.gz/refs/tags/v0.2.7.1
fi
ls -la v0271.tgz
tar tzf v0271.tgz >/dev/null 2>&1 && echo TAR_OK || { echo TAR_BROKEN; exit 2; }
rm -rf up0271 && mkdir -p up0271
tar xzf v0271.tgz -C up0271 --strip-components=1
echo "extracted files: $(find up0271 -type f | wc -l)"
echo
echo "=== local patches: src0271 vs upstream v0.2.7.1 (source dirs only) ==="
cd /home/albus/strata166
for d in src include serve tools tests; do
  [ -d "up0271_check/$d" ] && continue
  :
done
# compare with the extraction path
diff -rq --exclude=build-0271 --exclude=.git --exclude='*.o' --exclude='*.log' \
  /home/albus/strata166/src0271 /home/albus/strata166/dl/up0271 2>/dev/null \
  | grep -vE "^Only in /home/albus/strata166/src0271/(build|dl)" \
  | sed 's#/home/albus/strata166/src0271#SRC0271#g; s#/home/albus/strata166/dl/up0271#UP0271#g' \
  | head -80
