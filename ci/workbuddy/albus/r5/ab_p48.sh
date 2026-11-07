#!/bin/bash
# W818：不可复现是不是 `STRATA_ROUTE_TAIL_SKIP=7` 造成 —— 「miss 的专家按 rank 跳过」这个分支
# 依赖**专家缓存有没有命中**，而命中与否随请求演化 => 同一输入会走不同分支、不同归约顺序。
# 本车只切这一个变量（=0 关掉），其余全 = 生产，连发 6 次同输入看还有没有多吸引子。
set -u
cd /home/albus/strata166/tmp || exit 1
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
LOG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
OUT=/home/albus/strata166/data/w818_rtskip0_$(date +%Y%m%d_%H%M%S).txt
cp "$CFG" /tmp/w818_prod.json
DONE=0
restore() {
  [ "$DONE" = "1" ] && return 0
  DONE=1
  cp /tmp/w818_prod.json "$CFG"
  docker restart strata166-407 >/dev/null 2>&1
  for i in $(seq 1 900); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && break; sleep 1; done
  echo "  trap-restored" >> "$OUT"
}
trap restore EXIT

echo "# W818 RT_SKIP=0 determinism $(date +%F' '%T)" > "$OUT"
python3 - <<'PY' >> "$OUT"
import json
p = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"
d = json.load(open("/tmp/w818_prod.json"))
e = dict(d.get("env") or {})
e["STRATA_ROUTE_TAIL_SKIP"] = "0"
d["env"] = e
json.dump(d, open(p, "w"), indent=2, ensure_ascii=False)
print("  CFGCHECK env_n=%d rt_skip=%s" % (len(e), e["STRATA_ROUTE_TAIL_SKIP"]))
PY
ok=0
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 900); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { ok=$i; break; }; sleep 1; done
echo "=== READY ${ok}s" >> "$OUT"
grep -a -E "ROUTE_TAIL_SKIP|route tail" "$LOG" | tail -2 | cut -c1-150 | sed 's/^/  MODE /' >> "$OUT"
python3 mt_det2.py 8090 RSKIP0 dec_corpus.json 0 6 96 >> "$OUT" 2>&1

DONE=1
cp /tmp/w818_prod.json "$CFG"
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 900); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "restored ${i}s" >> "$OUT"; break; }; sleep 1; done
echo "== DONE $OUT"
