#!/bin/bash
# W842: 单臂 B（n4 + STRATA_SELECT_SIMT=2），与 A2（n4 + =1）单变量对比
# 温柔重启：docker stop -t 30 → 等 Exited → docker start（避开上一轮 26 s 就 Restarting 的现象）
set -u
C=strata166-407
DATA=/home/albus/strata166/data
CFG=$DATA/strata-huihui-ud-iq4_xs.json
LOG=/data/strata-huihui-ud-iq4_xs.log
STAMP=$(date +%H%M%S)
OUT=$DATA/w842_b_$STAMP.txt
cp "$CFG" /tmp/w842_b_base.json
restore() {
  cp /tmp/w842_b_base.json "$CFG" 2>/dev/null
  docker stop -t 30 "$C" >/dev/null 2>&1; docker start "$C" >/dev/null 2>&1
  for i in $(seq 1 480); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && break; sleep 1; done
  echo "  trap-restored $(date +%H:%M:%S)" >> "$OUT"
}
trap restore EXIT

python3 - "$CFG" <<'PYX' >> "$OUT"
import json, sys
cfg = sys.argv[1]
base = json.load(open("/tmp/w842_b_base.json"))
d = dict(base); d["exe"] = "/data/bin/strata-0.1.54n4"
e = dict(base.get("env") or {}); e["STRATA_SELECT_SIMT"] = "2"; d["env"] = e
assert set(d.keys()) == set(base.keys())
json.dump(d, open(cfg, "w"), indent=2, ensure_ascii=False)
print("cfg exe=n4 simt=2 env_n=%d" % len(e))
PYX

docker stop -t 30 "$C" >/dev/null 2>&1
for i in $(seq 1 60); do s=$(docker inspect -f '{{.State.Status}}' "$C"); [ "$s" = "exited" ] && break; sleep 1; done
echo "  stopped state=$(docker inspect -f '{{.State.Status}}' $C) $(date +%H:%M:%S)" >> "$OUT"
docker start "$C" >/dev/null 2>&1
ok=0
for i in $(seq 1 600); do
  curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { ok=$i; break; }
  if [ $((i % 30)) -eq 0 ]; then echo "  wait ${i}s status=$(docker inspect -f '{{.State.Status}}' $C)" >> "$OUT"; fi
  sleep 1
done
echo "=== ARM B (n4 + SIMT=2) ready=${ok}s $(date +%H:%M:%S)" >> "$OUT"
if [ "$ok" = "0" ]; then
  echo "  FAILED to start; docker logs:" >> "$OUT"
  docker logs --tail 40 "$C" 2>&1 >> "$OUT"
  exit 1
fi
docker exec "$C" bash -lc "grep -a 'qsa select' $LOG | tail -2" | sed 's/^/  SEL /' >> "$OUT"
( cd /home/albus/strata166/tmp && python3 mt_read.py 8090 B "$DATA/w842_read_B.json" 3718,6666,24000 2 kl_pool2.json 0 2 ) >> "$OUT" 2>&1
( cd /home/albus/strata166/tmp && python3 mt_gen.py 8090 B "$DATA/w842_gen_B.json" dec_corpus.json 200 3 ) >> "$OUT" 2>&1
docker exec "$C" bash -lc "grep -aE 'read in [0-9]+ ms' $LOG | tail -8" | sed 's/^/  READ /' >> "$OUT"
curl -s --max-time 8 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;e=json.load(sys.stdin)['engine'];print('  ENGINE slots=%d vram_free=%d' % (e['expert_slots'], e['vram_free_mib']))" >> "$OUT" 2>&1
echo "== DONE $OUT"
