#!/bin/bash
# 收尾核对：serve/ 全量（除字节码）、主线与容器、生产健康
R=/home/albus/strata166/pr/strata-fork
echo "=== serve/ comparison, pycache excluded, name+size ==="
docker exec strata166-407 sh -c 'cd /src/serve && find . -type f -not -path "./__pycache__/*" -printf "%s %p\n" | sort -k2' > /tmp/c.txt 2>/dev/null
cd "$R/serve" && find . -type f -not -path "./__pycache__/*" -printf '%s %p\n' | sort -k2 > /tmp/h.txt
echo "container=$(wc -l < /tmp/c.txt)  host=$(wc -l < /tmp/h.txt)"
echo "--- diff ---"; diff /tmp/c.txt /tmp/h.txt | head -12
echo "diff entries: $(diff /tmp/c.txt /tmp/h.txt | grep -c '^[<>]')"

echo
echo "=== the three runtime facts ==="
echo -n "1. engine binary running: "; docker exec strata166-407 ps -eo cmd 2>/dev/null | grep -o 'strata-0.1.55[a-z]' | head -1
echo -n "2. server code path: "; docker exec strata166-407 sh -c 'md5sum /src/serve/server.py' 2>/dev/null | cut -d' ' -f1
echo -n "   our branch:      "; md5sum "$R/serve/server.py" | cut -d' ' -f1
echo -n "3. health: "; curl -s --max-time 6 http://127.0.0.1:8090/health | head -c 60; echo

echo
echo "=== main line state ==="
cd "$R"
git rev-parse --abbrev-ref HEAD; git log --oneline -1
echo -n "vs upstream: "; git rev-list --left-right --count upstream/main...HEAD | awk '{print "behind "$1" / ahead "$2}'
echo -n "shallow: "; git rev-parse --is-shallow-repository
echo -n "heads on origin: "; git ls-remote --heads origin | wc -l
echo -n "tags on origin:  "; git ls-remote --tags origin | wc -l
