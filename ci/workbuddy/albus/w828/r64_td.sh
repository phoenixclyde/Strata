set -e
cd /home/albus/strata166
python3 - <<'PY'
import json
base=json.load(open('/home/albus/strata166/data/w828_ta.json'))
c=json.loads(json.dumps(base))
c['log']='/data/w828_td.log'
c['env']=dict(c['env'])
# three decode-side optimisations the gfx1151 table turns on and no discrete card has been measured with:
#   ATTN_LANECELL  decode attention scores, one cell per thread
#   MMVF_ROWS      bf16 multi-row GEMV, 4 rows per block
#   LFUSE          fewer launches around the shared expert and the KV append
c['env']['STRATA_ATTN_LANECELL']='1'
c['env']['STRATA_MMVF_ROWS']='1'
c['env']['STRATA_LFUSE']='1'
json.dump(c, open('/home/albus/strata166/data/w828_td.json','w'), ensure_ascii=False, indent=1)
print('td env:', sorted(k for k in c['env'] if k in ('STRATA_ATTN_LANECELL','STRATA_MMVF_ROWS','STRATA_LFUSE')))
print('args', len(c['args']), 'env', len(c['env']))
PY
cd /home/albus/strata166/tmp
pkill -f w828_ab2.sh 2>/dev/null || true
for a in ta td; do rm -f /home/albus/strata166/data/w828_ab2_$a.txt /home/albus/strata166/data/w828_$a.log; done
setsid nohup bash /home/albus/strata166/tmp/w828_ab2.sh ta td td ta > /home/albus/strata166/data/w828_ab4.log 2>&1 < /dev/null &
sleep 20
date +%H:%M:%S
docker ps --format '{{.Names}} {{.Status}}' | grep -E 'w828|strata166' || echo none
head -6 /home/albus/strata166/data/w828_ab4.log
