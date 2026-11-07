#!/bin/bash
W=/home/albus/strata166/src028/serve/web
echo "=== [1] max-width rules in css/js/html ==="
grep -rn "max-width" $W/*.css $W/*.js $W/*.html 2>/dev/null | head -40
echo
echo "=== [2] suspicious fixed widths (700-1100px) ==="
grep -rnoE "(max-)?width: *[0-9]{3,4}px" $W/*.css $W/*.html 2>/dev/null | sort -u | head -40
echo
echo "=== [3] monitor.html container classes ==="
grep -nE "class=\"[^\"]*(wrap|container|page|shell|main|grid)[^\"]*\"" $W/monitor.html 2>/dev/null | head -20
echo
echo "=== [4] index.html container classes ==="
grep -nE "class=\"[^\"]*(wrap|container|page|shell|main)[^\"]*\"" $W/index.html 2>/dev/null | head -20
echo
echo "=== [5] how monitor is embedded (tab or iframe?) ==="
grep -n "monitor" $W/index.html 2>/dev/null | head -20
