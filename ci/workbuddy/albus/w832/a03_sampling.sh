#!/bin/bash
S=/home/albus/strata166/src028
echo "=== [1] sampling 从请求的哪里来 ==="
grep -n "sampling = \|sampling=" $S/serve/server.py | head -20
echo
echo "=== [2] chat completions 的 body 解析（找 sampling / extra） ==="
grep -n "def chat\|body.get(\"sampling\")\|\[\"sampling\"\]" $S/serve/server.py | head -20
echo
echo "=== [3] 上下文：sampling 构造处 ==="
grep -n "sampling" $S/serve/server.py | sed -n '1,25p'
