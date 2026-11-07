S=/home/albus/strata166/src028
echo "=== W776: is STRATA_USE_HIP scoped to dflash2.cpp in the build? ==="
python3 - <<'PY'
import json
cc = json.load(open('/home/albus/strata166/src028/build-028r/compile_commands.json'))
for e in cc:
    if e['file'].endswith('src/core/dflash2.cpp'):
        cmd = e.get('command') or ' '.join(e.get('arguments') or [])
        print('  dflash2.cpp has -DSTRATA_USE_HIP:', 'STRATA_USE_HIP' in cmd)
        # and confirm it is NOT global
        break
n = sum(1 for e in cc if 'STRATA_USE_HIP' in (e.get('command') or ' '.join(e.get('arguments') or [])))
print('  files compiled with STRATA_USE_HIP:', n, '(should be 1)')
PY
echo
echo "=== the telemetry apply script: does it touch anything besides telemetry.py? ==="
sed -n '1,40p' /home/albus/strata166/patches/apply_telemetry_pcie.sh
echo
echo "=== this boot's prefill / cache / version banners ==="
CFG=/data/strata-huihui-ud-iq4_xs.json
LOG=$(docker exec strata166-407 bash -lc "python3 -c \"import json;print(json.load(open('$CFG')).get('log'))\"" | tr -d '\r')
docker exec strata166-407 bash -lc "grep -aE 'prompt chunk|expert cache|PROMPT_F16|engine started' '$LOG' | tail -5 | cut -c1-170"
