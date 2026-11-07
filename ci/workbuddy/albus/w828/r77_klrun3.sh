set -e
cd /home/albus/strata166
python3 - <<'PY'
import json
for name, out in (('w828_kle0','/data/w828kl/E0r.tsv'), ('w828_kle0b','/data/w828kl/E0br.tsv'), ('w828_kleall','/data/w828kl/Eallr.tsv')):
    p='/home/albus/strata166/data/%s.json'%name
    c=json.load(open(p))
    c['env']['STRATA_LOGPOS']=out
    c['log']='/data/%s_r.log'%name
    json.dump(c, open(p,'w'), ensure_ascii=False, indent=1)
    print(name, '->', out, '| kv', c['args'][c['args'].index('--kv')+1], '| rt_skip', c['env'].get('STRATA_ROUTE_TAIL_SKIP'))
PY
cd /home/albus/strata166/tmp
pkill -f w828_arm.sh 2>/dev/null || true
setsid nohup bash -c '
bash /home/albus/strata166/tmp/w828_arm5.sh e0   /data/w828_kle0.json   w828e0   /data/w828kl/E0r.tsv   8
bash /home/albus/strata166/tmp/w828_arm5.sh e0b  /data/w828_kle0b.json  w828e0b  /data/w828kl/E0br.tsv  8
bash /home/albus/strata166/tmp/w828_arm5.sh eall /data/w828_kleall.json w828eall /data/w828kl/Eallr.tsv 8
' > /home/albus/strata166/data/w828_kl3.log 2>&1 < /dev/null &
sleep 22
date +%H:%M:%S
docker ps --format '{{.Names}} {{.Status}}' | grep -E 'w828|strata166' || echo none
head -6 /home/albus/strata166/data/w828_kl3.log
