#!/bin/bash
W=/home/albus/strata166/src028/serve/web
echo "=== md5 of deployed web assets ==="
md5sum $W/app.css $W/app.js $W/index.html $W/monitor.html 2>/dev/null
echo
echo "=== other trees on disk that hold a web dir ==="
for d in /tmp/srcx/*/serve/web /home/albus/strata166/src*/serve/web /home/albus/strata166/src2*/serve/web; do
  [ -d "$d" ] && echo "$d  $(md5sum $d/app.css 2>/dev/null | cut -d' ' -f1)  $(stat -c %y $d/app.css 2>/dev/null | cut -d. -f1)"
done | sort -u
echo
echo "=== .monitor / .about / .chat width rules in every tree ==="
for f in /tmp/srcx/*/serve/web/app.css /home/albus/strata166/src*/serve/web/app.css; do
  [ -f "$f" ] || continue
  echo "### $f"
  grep -nE "^\.(monitor|about|chat)[ ,{]" "$f" 2>/dev/null | head -6
done
