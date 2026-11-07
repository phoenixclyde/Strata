#!/bin/bash
set -e
W=/home/albus/strata166/src028/serve/web
C=$W/app.css
echo "=== box-sizing reset present? ==="
grep -rn "box-sizing" $W/*.css | head -5
echo
echo "=== backup ==="
[ -f "$C.bak-w831" ] || cp -a "$C" "$C.bak-w831"
ls -la "$C.bak-w831"
echo
echo "=== append override (idempotent) ==="
if grep -q "ALBUS-W831" "$C"; then
  echo "already patched"
else
  cat >> "$C" <<'EOF'

/* --- ALBUS-W831 (local patch; registry: deploy/patches/LOCAL_PATCHES.tsv) -------------
   Upstream v0.2.7.1 capped the dashboard at min(100%, 1920px). On a 2560-wide window that
   leaves ~320px dead on each side. Restore the pre-0.2.7.1 behaviour: fill the window.
   Scoped to .monitor only -- .about / .chat keep their upstream caps. */
.monitor { max-width: none; }
EOF
  echo "appended"
fi
echo
echo "=== result ==="
tail -10 "$C"
echo
grep -n "^\.monitor { max-width: none; }" "$C"
md5sum "$C"
wc -c "$C"
