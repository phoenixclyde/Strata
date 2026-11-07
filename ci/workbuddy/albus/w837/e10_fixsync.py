import io

p = 'D:/workbuddy_space/strata_ws/albus/w836/sync_gfx906.sh'
s = io.open(p, encoding='utf-8').read()

old_files = 'FILES="CMakeLists.txt src/kernels/cuda/qsa_decode_attn.cu serve/telemetry.py serve/web/app.css serve/web/app.js"'
new_files = ('FILES="src/kernels/cuda/qsa_decode_attn.cu serve/telemetry.py serve/web/app.css serve/web/app.js '
             'include/strata/platform/hip_compat/strata_hip.h include/strata/kernels/gfx_arch.hpp '
             'include/strata/core/arch_defaults.hpp src/core/arch_defaults.cpp src/core/arch_defaults_test.cpp"')
assert s.count(old_files) == 1
s = s.replace(old_files, new_files, 1)

old3 = '''say "=== 3. drift between branch and build tree ==="
drift=0
for f in $FILES; do'''
new3 = '''say "=== 3. drift between branch and build tree ==="
# CMakeLists.txt is deliberately NOT synced as a file: the branch carries upstream main's copy plus our
# hunks, while src028 carries v0.2.8's plus the same hunks.  Copying it would drag upstream's later
# changes into the build tree.  Check the patch markers instead.
cm_ok=1
for m in W793 "W776 local"; do
  n=$(grep -c "$m" "$DST/CMakeLists.txt" 2>/dev/null || echo 0)
  [ "$n" -ge 1 ] && printf "  marker %-12s present in src028\\n" "$m" || { printf "  marker %-12s MISSING in src028\\n" "$m"; cm_ok=0; }
done
[ "$cm_ok" -eq 1 ] || drift_note="CMakeLists.txt markers missing"
drift=0
for f in $FILES; do'''
assert s.count(old3) == 1, s.count(old3)
s = s.replace(old3, new3, 1)

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('sync script updated')
print('  CMakeLists removed from FILES:', 'CMakeLists.txt src/' not in s)
print('  new FILES line:', [l for l in s.split('\n') if l.startswith('FILES=')][0][:150])
