#!/bin/bash
# W844 落产：引擎 0.1.54n4 → 0.1.55g（v0.2.9 树），镜像仍 0.2.8p2（serve 层未换）
# 失败自动回滚到 n4；成功则跑门禁 + 三条冒烟探针
set -u
C=strata166-407
DATA=/home/albus/strata166/data
CFG=$DATA/strata-huihui-ud-iq4_xs.json
OUT=$DATA/w844_deploy_$(date +%H%M%S).txt
cp "$CFG" /tmp/w844_deploy_base.json

rollback() {
  cp /tmp/w844_deploy_base.json "$CFG" 2>/dev/null
  docker stop -t 30 "$C" >/dev/null 2>&1; docker start "$C" >/dev/null 2>&1
  for i in $(seq 1 480); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && break; sleep 1; done
  echo "  ROLLED BACK to $(python3 -c "import json;print(json.load(open('$CFG'))['exe'])")" >> "$OUT"
}
trap rollback EXIT

python3 - "$CFG" <<'PYX' >> "$OUT"
import json, sys
cfg = sys.argv[1]
base = json.load(open("/tmp/w844_deploy_base.json"))
d = dict(base); d["exe"] = "/data/bin/strata-0.1.55g"
assert set(d.keys()) == set(base.keys())
json.dump(d, open(cfg, "w"), indent=2, ensure_ascii=False)
print("cfg -> exe=/data/bin/strata-0.1.55g  args=%d env=%d" % (len(d["args"]), len(d.get("env") or {})))
PYX

docker stop -t 30 "$C" >/dev/null 2>&1
for i in $(seq 1 60); do [ "$(docker inspect -f '{{.State.Status}}' $C)" = "exited" ] && break; sleep 1; done
docker start "$C" >/dev/null 2>&1
ok=0
for i in $(seq 1 600); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { ok=$i; break; }; sleep 1; done
echo "  health ready=${ok}s $(date +%H:%M:%S)" >> "$OUT"
if [ "$ok" = "0" ]; then echo "  FAILED: 未就绪，回滚" >> "$OUT"; exit 1; fi

echo "=== /health ===" >> "$OUT"
curl -s http://127.0.0.1:8090/health >> "$OUT"; echo >> "$OUT"
echo "=== /metrics engine 段 ===" >> "$OUT"
curl -s http://127.0.0.1:8090/metrics | python3 -c "import sys,json;d=json.load(sys.stdin);e=d['engine'];print({k:e.get(k) for k in ('expert_slots','vram_free_mib','pcie_frac')});print('requests',d.get('totals',{}).get('requests'))" >> "$OUT" 2>&1
echo "=== 冒烟：一条 read + 一条 decode（不入账，仅证明能服务） ===" >> "$OUT"
( cd /home/albus/strata166/tmp && python3 mt_read.py 8090 smoke "$DATA/w844_smoke.json" 3718 1 kl_pool2.json 0 2 ) >> "$OUT" 2>&1
( cd /home/albus/strata166/tmp && python3 mt_gen.py 8090 smoke "$DATA/w844_gen_smoke.json" dec_corpus.json 128 1 ) >> "$OUT" 2>&1
echo "=== 引擎启动行 ===" >> "$OUT"
docker exec "$C" bash -lc "grep -a 'engine started' /data/strata-huihui-ud-iq4_xs.log | tail -1" >> "$OUT" 2>&1
trap - EXIT
echo "DEPLOYED $(date +%H:%M:%S)" >> "$OUT"
echo "== DONE $OUT"
