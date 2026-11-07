#!/bin/bash
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
LOG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
echo "=== container ==="
docker ps --format '{{.Names}} {{.Image}} {{.Status}}' | grep strata
echo "=== engine (must be 0.1.55h, no WAVE_ROWS env) ==="
grep -a "engine started" "$LOG" | tail -1 | cut -c1-110
docker exec strata166-407 ps -eo cmd 2>/dev/null | grep -c "strata-0.1.55h"
echo "=== config ==="
md5sum "$CFG"
python3 -c "import json;d=json.load(open('$CFG'));print('exe=',d['exe']);print('env=',sorted(d.get('env',{}).items()))"
echo "=== health / vram ==="
curl -s --max-time 6 http://127.0.0.1:8090/health; echo
rocm-smi --showmeminfo vram 2>/dev/null | grep Used
echo "=== binaries ==="
md5sum /home/albus/strata166/data/bin/strata-0.1.55g /home/albus/strata166/data/bin/strata-0.1.55h
echo "=== source tree ==="
cd /home/albus/strata166/pr/strata-fork && git status --porcelain
echo "=== rollback point exists ==="
ls -1 /home/albus/strata166/data/strata-huihui-ud-iq4_xs.json.bak_w863ab_* 2>/dev/null | tail -2
