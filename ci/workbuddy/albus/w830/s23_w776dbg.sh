S=/home/albus/strata166/src028
echo "=== the inserted block, as it now stands in CMakeLists.txt ==="
grep -n -B3 -A6 "W776 local" "$S/CMakeLists.txt"
echo
echo "=== dflash2 in build.ninja: which target and which defines ==="
grep -n "dflash2" "$S/build-028r/build.ninja" | head -6
python3 - <<'PY'
import re
t = open('/home/albus/strata166/src028/build-028r/build.ninja').read()
# find the build rule for dflash2 and print its DEFINES line
blocks = t.split('build ')
for b in blocks:
    if 'dflash2.cpp.o' in b:
        lines = b.split('\n')
        print(' build:', lines[0][:140])
        for l in lines[1:]:
            if 'DEFINES' in l or 'FLAGS' in l:
                print('   ', l[:300])
        break
PY
echo
echo "=== is dflash2.cpp actually listed as a source of strata_engine? ==="
grep -rn "dflash2.cpp" "$S/CMakeLists.txt" | head -4
