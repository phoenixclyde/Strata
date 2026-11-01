#!/bin/bash
# strata-ci rollback -- put production back on a previous engine.  No rebuild, ~5 minutes
# (most of it is the engine's own 4-minute load).
#
# Two ways to say what to go back to:
#   --exe strata-0.1.55g        an explicit file in /data/bin
#   --last                      the entry before the current one in the ledger
#
# Usage: rollback.sh (--exe NAME | --last) [--apply]
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/config.sh"

TARGET=""
LAST=0
APPLY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --exe) TARGET=$2; shift 2 ;;
    --last) LAST=1; shift ;;
    --apply) APPLY=1; shift ;;
    *) echo "unknown arg: $1"; exit 2 ;;
  esac
done

if [ "$LAST" = "1" ] || [ -z "$TARGET" ]; then
  [ -f "$HISTORY" ] || { echo "no ledger at $HISTORY -- pass --exe"; exit 2; }
  TARGET=$(tail -2 "$HISTORY" | head -1 | cut -f2)
  echo "ledger: previous entry is '$TARGET'"
fi

[ -n "$TARGET" ] || { echo "nothing to roll back to"; exit 2; }
[ -f "$BIN/$TARGET" ] || { echo "missing binary: $BIN/$TARGET"; ls -l "$BIN" | tail -5; exit 2; }

CUR=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["exe"])' "$CFG")
echo "current  : $CUR"
echo "rollback : /data/bin/$TARGET"
md5sum "$BIN/$TARGET"

if [ "$APPLY" != "1" ]; then
  echo
  echo "[dry-run] would back up the config, set exe=/data/bin/$TARGET, restart $CONTAINER."
  echo "          re-run with --apply"
  exit 0
fi

TS=$(date +%Y%m%d_%H%M%S)
cp -f "$CFG" "$BACKUPS/$(basename "$CFG").rollback_$TS"
python3 - "$CFG" "$TARGET" <<'PY'
import json, sys
p, name = sys.argv[1], sys.argv[2]
d = json.load(open(p))
old = d.get("exe")
d["exe"] = "/data/bin/" + name
json.dump(d, open(p, "w"), indent=2, ensure_ascii=False)
print("exe:", old, "->", d["exe"])
PY

echo "=== restart ==="
docker restart "$CONTAINER" >/dev/null 2>&1 || { echo "restart failed"; exit 1; }
OK=0
for i in $(seq 1 "${HEALTH_TIMEOUT:-420}"); do
  if curl -s --max-time 2 "$HEALTH" >/dev/null 2>&1; then OK=$i; break; fi
  sleep 1
done
[ "$OK" != "0" ] || { echo "no health answer"; exit 1; }
sleep 6
H=$(curl -s --max-time 6 "$HEALTH")
echo "health after ${OK}s: $H"
VRAM=$(rocm-smi --showmeminfo vram 2>/dev/null | grep -i 'Used' | head -1 | grep -o '[0-9]*$')
case "$H" in *'"status": "ok"'*) echo "OK: service healthy on $TARGET";;
  *) echo "GATE FAIL: health not ok after rollback"; exit 1 ;; esac
printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
  "$(date -Is)" "$TARGET" "$(md5sum "$BIN/$TARGET" | cut -d' ' -f1)" \
  "$(md5sum "$CFG" | cut -d' ' -f1)" "$(git -C "$REPO" rev-parse HEAD)" "ROLLBACK" \
  "$OK" "${VRAM:-?}" "-" >> "$HISTORY"
echo "ledger: $(tail -1 "$HISTORY")"
