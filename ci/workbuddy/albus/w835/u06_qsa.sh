#!/bin/bash
# W835: KI's own Qwen3.8-Flash-Next / QSA records -- same model as ours
K=/home/albus/routeK/base/KIntegrated-mobydick
cd $K || exit 1
echo "=== A. DEVLOG-qwen38-flash-qsa.md : verdict lines ==="
git show FETCH_HEAD:docs/gfx906/DEVLOG-qwen38-flash-qsa.md 2>/dev/null | grep -nE "VERDICT|SHIPPED|DEAD|NO-GO|NEUTRAL|\+[0-9]+[.][0-9] ?%|-[0-9]+[.][0-9] ?%|t/s" | head -50
echo
echo "=== B. its head (what the model is) ==="
git show FETCH_HEAD:docs/gfx906/DEVLOG-qwen38-flash-qsa.md 2>/dev/null | head -40
echo
echo "=== C. qsa-tester-build/README.md head ==="
git show FETCH_HEAD:docs/gfx906/qsa-tester-build/README.md 2>/dev/null | head -45
