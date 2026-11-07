#!/bin/bash
# W815：启动那 173 s 能不能快 —— `STRATA_UNBUFFERED_LOAD=1`
#   本构建的 Linux 上，这个开关**只把 reader 数从 6 提到 16**（上游 #3624 逐字：
#   "There, STRATA_UNBUFFERED_LOAD=1 only raises the reader count to 16, and the load still runs at the
#    page-cache path's speed"），**没有 O_DIRECT**（那是 #3624 这个 open PR 才加的）。
#   所以在 SATA 上预期无收益；本车是为了把「没收益」这件事**量出来**，而不是靠推断。
set -u
cd /home/albus/strata166/tmp || exit 1
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
LOG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
OUT=/home/albus/strata166/data/w815_unbuf_$(date +%Y%m%d_%H%M%S).txt
cp "$CFG" /tmp/w815_prod.json
DONE=0
restore() {
  [ "$DONE" = "1" ] && return 0
  DONE=1
  cp /tmp/w815_prod.json "$CFG"
  docker restart strata166-407 >/dev/null 2>&1
  for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && break; sleep 1; done
  echo "restored" >> "$OUT"
}
trap restore EXIT

echo "# W815 unbuffered-load probe $(date +%F' '%T)" > "$OUT"
for A in P U; do
  python3 - "$CFG" "$A" <<'PY' >> "$OUT"
import json, sys
cfg, arm = sys.argv[1], sys.argv[2]
d = json.load(open("/tmp/w815_prod.json"))
e = dict(d.get("env") or {})
e.pop("STRATA_UNBUFFERED_LOAD", None)
if arm == "U":
    e["STRATA_UNBUFFERED_LOAD"] = "1"
d["env"] = e
json.dump(d, open(cfg, "w"), indent=2, ensure_ascii=False)
print("  ARM %s env_n=%d unbuffered=%s" % (arm, len(e), e.get("STRATA_UNBUFFERED_LOAD", "-")))
PY
  T0=$(date +%s); ok=0
  docker restart strata166-407 >/dev/null 2>&1
  for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { ok=$i; break; }; sleep 1; done
  T1=$(date +%s)
  echo "=== ARM $A ready=$((T1-T0))s" >> "$OUT"
  grep -a "loaded 55.43 GiB at" "$LOG" | tail -1 | sed 's/^/  LOAD /' >> "$OUT"
  grep -a "native projection matrices" "$LOG" | tail -1 | sed 's/^/  PROJ /' >> "$OUT"
  grep -a "expert arena read through" "$LOG" | tail -1 | sed 's/^/  PATH /' >> "$OUT"
done
DONE=1
cp /tmp/w815_prod.json "$CFG"
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "restored ${i}s" >> "$OUT"; break; }; sleep 1; done
echo "== DONE $OUT"
