#!/bin/bash
# strata-ci deploy -- put a built engine into production, or explain exactly what it would do.
#
# Default is a DRY RUN.  Nothing is copied, no service is restarted, until --apply.
#
# Order is deliberate: every step that can say "no" runs before anything changes.
#   1 gate        (source + build + live config, ci/gate.py)
#   2 tag         (a deployable commit must carry mi50-*; --allow-untagged overrides)
#   3 identity    (the new binary must actually contain what the source says: symbol + env)
#   4 install     cp -> .new -> mv   (a half-written binary never sits at the live path)
#   5 config      backup, then point exe at the new file
#   6 restart     and wait for /health
#   7 verify      health + weight accounting + VRAM, then write the ledger line
#
# Usage: deploy.sh [--src DIR] [--exe NAME] [--apply] [--allow-untagged] [--timeout S]
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/config.sh"

SRCDIR=$BUILD
EXENAME=""
APPLY=0
ALLOW_UNTAGGED=0
while [ $# -gt 0 ]; do
  case "$1" in
    --src) SRCDIR=$2; shift 2 ;;
    --exe) EXENAME=$2; shift 2 ;;
    --apply) APPLY=1; shift ;;
    --allow-untagged) ALLOW_UNTAGGED=1; shift ;;
    --timeout) HEALTH_TIMEOUT=$2; shift 2 ;;
    *) echo "unknown arg: $1"; exit 2 ;;
  esac
done

say() { printf '\n=== %s ===\n' "$*"; }
fail() { printf '\nDEPLOY STOPPED: %s\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------- 0 github
# W1029: the gate that counts is the one that runs where the change lands.  GitHub Actions
# must have a completed, successful run for THIS commit; the local round gate is convenience.
say "0/8 github gate"
python3 "$HERE/gh_gate.py" --sha "$(git -C "$REPO" rev-parse HEAD)" \
  || fail "GitHub CI has no green run for HEAD (push it, then: ci/gh_gate.py --wait 300)"
# Secondary, and deliberately non-fatal: the receiving-end receipt from W1028.  It is a
# second pair of eyes, not the record of truth (that is the GitHub run above).
python3 "$HERE/gate_receipt.py" --sha "$(git -C "$REPO" rev-parse HEAD)" \
  || echo "note: no local gate receipt for HEAD (GitHub run is what gates this deploy)"

# ---------------------------------------------------------------- 1 gate
say "1/7 gate"
python3 "$HERE/gate.py" --repo "$REPO" --build "$BUILD" --config "$CFG" || fail "gate"

# ---------------------------------------------------------------- 2 tag
say "2/7 release tag"
HEAD_SHA=$(git -C "$REPO" rev-parse HEAD)
TAG=$(git -C "$REPO" describe --exact-match --match "${TAG_PREFIX}*" HEAD 2>/dev/null || true)
echo "HEAD    = ${HEAD_SHA:0:10}"
echo "tag     = ${TAG:-<none>}"
BRANCH=$(git -C "$REPO" rev-parse --abbrev-ref HEAD)
echo "branch  = $BRANCH"
if [ -n "$(git -C "$REPO" status --porcelain --untracked-files=no)" ]; then
  echo "WARNING: tracked files are modified -- the binary would not match any commit"
  git -C "$REPO" status --porcelain --untracked-files=no | head -5
fi
if [ -z "$TAG" ] && [ "$ALLOW_UNTAGGED" != "1" ]; then
  fail "HEAD carries no ${TAG_PREFIX}* tag (pass --allow-untagged to override)"
fi

# ---------------------------------------------------------------- 3 identity
say "3/7 new binary identity"
NEW=$SRCDIR/strata
[ -f "$NEW" ] || fail "no binary at $NEW"
NEW_MD5=$(md5sum "$NEW" | cut -d' ' -f1)
NEW_SIZE=$(stat -c%s "$NEW")
SYM=$(nm -C "$NEW" 2>/dev/null | grep -c 'wave_rows_for\|kWaveRows')
ENVS=$(strings -a "$NEW" | grep -c STRATA_MMVQ_WAVE_ROWS)
echo "md5=$NEW_MD5  size=$NEW_SIZE  wave_rows_symbols=$SYM  wave_rows_env_strings=$ENVS"
[ "$SYM" -ge 1 ] || fail "the new binary has no wave_rows symbol -- the R table would be missing"
[ "$ENVS" -ge 1 ] || fail "the new binary has no STRATA_MMVQ_WAVE_ROWS string -- no runtime rollback"
"$NEW" --version 2>&1 | head -1

# ---------------------------------------------------------------- 4 install
if [ -z "$EXENAME" ]; then
  EXENAME=$(python3 - "$CFG" <<'PY'
import json, re, sys
cur = json.load(open(sys.argv[1])).get("exe", "")
m = re.search(r"strata-(\d+\.\d+\.\d+)([a-z])(\.new)?$", cur)
if not m:
    print("strata-next"); raise SystemExit
ver, ch = m.group(1), m.group(2)
print("strata-%s%s" % (ver, chr(ord(ch) + 1)))
PY
)
fi
TARGET=$BIN/$EXENAME
# ---------------------------------------------------------------- 3.5/8 evidence gate
# W1035: 装机必须带 A/B 与数值证据。没有证据 => 不装（判据，不是判断）。
say "3.5/8 evidence gate (A/B + numeric)"
EVID=${EVIDENCE:-$REPO/ci/state/ab/latest.json}
python3 "$HERE/deploy_gate.py" --path "$NEW" --exe "$EXENAME" --ab "$EVID" --live \
  || fail "deploy gate REFUSE for $EXENAME: no A/B or numeric evidence (see above); expected at $EVID"
say "4/7 install -> $TARGET"
echo "from: $NEW"
if [ -f "$TARGET" ]; then
  T_MD5=$(md5sum "$TARGET" | cut -d' ' -f1)
  echo "existing $EXENAME md5=$T_MD5"
  [ "$T_MD5" = "$NEW_MD5" ] && echo "(same content -- install is a no-op)"
fi
if [ "$APPLY" = "1" ]; then
  cp -f "$NEW" "$TARGET.new" && chmod 755 "$TARGET.new" && mv -f "$TARGET.new" "$TARGET"
  echo "installed: $(md5sum "$TARGET")"
else
  echo "[dry-run] cp $NEW $TARGET.new && mv $TARGET.new $TARGET"
fi

# ---------------------------------------------------------------- 5 config
say "5/7 config"
CUR_EXE=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["exe"])' "$CFG")
echo "current exe: $CUR_EXE"
echo "new     exe: /data/bin/$EXENAME"
if [ "$APPLY" = "1" ]; then
  TS=$(date +%Y%m%d_%H%M%S)
  cp -f "$CFG" "$BACKUPS/$(basename "$CFG").$TS"
  echo "backup -> $BACKUPS/$(basename "$CFG").$TS"
  python3 - "$CFG" "$EXENAME" <<'PY'
import json, sys
p, name = sys.argv[1], sys.argv[2]
d = json.load(open(p))
old = d.get("exe")
d["exe"] = "/data/bin/" + name
json.dump(d, open(p, "w"), indent=2, ensure_ascii=False)
print("exe:", old, "->", d["exe"])
PY
else
  echo "[dry-run] backup config, set exe = /data/bin/$EXENAME"
fi

# ---------------------------------------------------------------- 6 restart
say "6/7 restart + wait for health"
W_BEFORE=$(grep -a "native projection matrices" "$ELOG" 2>/dev/null | tail -1 | grep -o '[0-9]* native projection matrices, [0-9.]* MiB' || true)
echo "weights before: ${W_BEFORE:-<unknown>}"
T0=$(date +%s)
if [ "$APPLY" = "1" ]; then
  docker restart "$CONTAINER" >/dev/null 2>&1 || fail "docker restart $CONTAINER failed"
else
  echo "[dry-run] docker restart $CONTAINER"
  echo
  echo "dry run complete -- nothing changed.  Re-run with --apply."
  exit 0
fi
OK=0
for i in $(seq 1 "$HEALTH_TIMEOUT"); do
  if curl -s --max-time 2 "$HEALTH" >/dev/null 2>&1; then OK=$i; break; fi
  sleep 1
done
[ "$OK" != "0" ] || fail "no health answer within ${HEALTH_TIMEOUT}s"
sleep 6
HEALTH_JSON=$(curl -s --max-time 6 "$HEALTH")
echo "health after ${OK}s: $HEALTH_JSON"

# ---------------------------------------------------------------- 7 verify
say "7/7 verify + ledger"
W_AFTER=$(grep -a "native projection matrices" "$ELOG" 2>/dev/null | tail -1 | grep -o '[0-9]* native projection matrices, [0-9.]* MiB' || true)
VRAM=$(rocm-smi --showmeminfo vram 2>/dev/null | grep -i 'Used' | head -1 | grep -o '[0-9]*$')
CFG_MD5=$(md5sum "$CFG" | cut -d' ' -f1)
echo "weights after : ${W_AFTER:-<unknown>}"
echo "vram used     : ${VRAM:-?} bytes"
echo "cfg md5       : $CFG_MD5"

FAILED=0
case "$HEALTH_JSON" in *'"status": "ok"'*) ;; *) echo "GATE FAIL: health not ok"; FAILED=1 ;; esac
case "$HEALTH_JSON" in *'"loaded": true'*) ;; *) echo "GATE FAIL: model not loaded"; FAILED=1 ;; esac
if [ -n "$W_BEFORE" ] && [ -n "$W_AFTER" ] && [ "$W_BEFORE" != "$W_AFTER" ]; then
  echo "WARNING: weight accounting changed: '$W_BEFORE' -> '$W_AFTER'"
fi

if [ ! -f "$HISTORY" ]; then
  printf 'ts\texe\texe_md5\tcfg_md5\tgit_head\ttag\thealth_s\tvram_used\tweights\n' > "$HISTORY"
fi
printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
  "$(date -Is)" "$EXENAME" "$NEW_MD5" "$CFG_MD5" "$HEAD_SHA" "${TAG:--}" "$OK" "${VRAM:-?}" "${W_AFTER:--}" >> "$HISTORY"
echo "ledger: $HISTORY"
tail -2 "$HISTORY"
[ "$FAILED" = "0" ] || fail "post-deploy gates"
echo
echo "rollback: ci/rollback.sh --exe $CUR_EXE --apply"
