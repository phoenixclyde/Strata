set -e
cd /home/albus/strata166
grep -q 'EXIT=0' src028/build-028.log || { echo "BUILD NOT OK:"; tail -3 src028/build-028.log; exit 1; }
tail -2 src028/build-028.log
ls -la src028/build-028/strata
cp -f src028/build-028/strata data/bin/strata-0.1.54n
chmod 755 data/bin/strata-0.1.54n
ls -la data/bin/
echo "--- version ---"
docker run --rm -v /home/albus/strata166/data:/data strata-gfx906:0.2.4p4 /data/bin/strata-0.1.54n --version 2>&1 | head -3
echo "--- new 0.1.54 markers in the binary ---"
strings data/bin/strata-0.1.54n | grep -m3 -E 'a speculative window holds|verify / batch windows|what is allocated after the cache' || echo "(none)"
echo "--- old binary untouched ---"
md5sum data/bin/strata-0.1.53 data/bin/strata-0.1.54n
