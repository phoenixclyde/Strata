#!/bin/bash
# W819：不可复现的元凶到底是不是 `STRATA_PREFILL_CPU_SHARE=auto`
#   线索来自我们自己的 W802/W803 记录：**开 share 后 prefill 逐次不同**，而 **share=0 时两遍 md5 完全相同**。
#   若成立，机制就是：同一个提示每次 prefill 的字节不同 -> KV 不同 -> 贪心解码从早期就分叉。
#   本车只切这一个变量：share=0，其余全 = 生产，连发 6 次同输入。
set -u
cd /home/albus/strata166/tmp || exit 1
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
LOG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
OUT=/home/albus/strata166/data/w819_share0_$(date +%Y%m%d_%H%M%S).txt
cp "$CFG" /tmp/w819_prod.json
DONE=0
restore() {
  [ "$DONE" = "1" ] && return 0
  DONE=1
  cp /tmp/w819_prod.json "$CFG"
  docker restart strata166-407 >/dev/null 2>&1
  for i in $(seq 1 900); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && break; sleep 1; done
  echo "  trap-restored" >> "$OUT"
}
trap restore EXIT

echo "# W819 share=0 determinism $(date +%F' '%T)" > "$OUT"
python3 - <<'PY' >> "$OUT"
import json
p = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"
d = json.load(open("/tmp/w819_prod.json"))
e = dict(d.get("env") or {})
e["STRATA_PREFILL_CPU_SHARE"] = "0"
d["env"] = e
json.dump(d, open(p, "w"), indent=2, ensure_ascii=False)
print("  CFGCHECK env_n=%d share=%s max=%s" % (len(e), e["STRATA_PREFILL_CPU_SHARE"], e.get("STRATA_PREFILL_CPU_SHARE_MAX")))
PY
ok=0
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 900); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { ok=$i; break; }; sleep 1; done
echo "=== READY ${ok}s" >> "$OUT"
grep -a -E "cpu share|share 0\.|on the CPU" "$LOG" | tail -2 | cut -c1-140 | sed 's/^/  MODE /' >> "$OUT"
python3 mt_det2.py 8090 SHARE0 dec_corpus.json 0 6 96 >> "$OUT" 2>&1
# 再连发一轮，看跨两轮是否也一致
python3 mt_det2.py 8090 SHARE0b dec_corpus.json 0 4 96 >> "$OUT" 2>&1

DONE=1
cp /tmp/w819_prod.json "$CFG"
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 900); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "restored ${i}s" >> "$OUT"; break; }; sleep 1; done
echo "== DONE $OUT"
