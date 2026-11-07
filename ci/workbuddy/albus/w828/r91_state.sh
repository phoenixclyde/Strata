date +%H:%M:%S
echo "--- containers ---"
docker ps -a --format '{{.Names}} {{.Status}}' | grep -Ei 'w828|strata' || echo none
echo "--- prod health ---"
curl -s --max-time 4 http://127.0.0.1:8090/health | head -c 130; echo
echo "--- prod config fingerprint (untouched?) ---"
md5sum /home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
ls -la /home/albus/strata166/data/strata-huihui-ud-iq4_xs.json.bak-w828h 2>/dev/null | awk '{print $5, $9}'
echo "--- prod args/env counts ---"
python3 -c "
import json;c=json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'))
a=c['args']
print('exe', c['exe']); print('nargs', len(a), 'nenv', len(c.get('env') or {}))
print('spec', a[a.index('--spec')+1], 'minp', a[a.index('--spec-min-p')+1], 'pcie', a[a.index('--pcie-frac')+1])
"
echo "--- arm configs left on disk (small, kept for replay) ---"
du -ch /home/albus/strata166/data/w828_*.json 2>/dev/null | tail -1
