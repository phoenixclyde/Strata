#!/bin/bash
# W863 · 部署 0.1.55h（R 表实测版）+ 把 config 的 exe 指过去
# 回滚：把 config 的 exe 改回 /data/bin/strata-0.1.55g（旧文件原样保留）
set -u
B=/home/albus/strata166/gfx029-build
D=/home/albus/strata166/data/bin
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
TS=$(date +%Y%m%d_%H%M%S)

echo "=== new binary identity ==="
md5sum "$B/strata"; stat -c "%s bytes" "$B/strata"
echo "symbols=$(nm -C "$B/strata" 2>/dev/null | grep -c 'wave_rows_for|kWaveRows')" 
echo "env-string=$(strings -a "$B/strata" | grep -c STRATA_MMVQ_WAVE_ROWS)"
"$B/strata" --version 2>&1 | head -1

echo "=== install as strata-0.1.55h (cp -> .new -> mv) ==="
cp -f "$B/strata" "$D/strata-0.1.55h.new" && chmod 755 "$D/strata-0.1.55h.new" && mv -f "$D/strata-0.1.55h.new" "$D/strata-0.1.55h"
ls -l "$D/strata-0.1.55h" "$D/strata-0.1.55g"
md5sum "$D/strata-0.1.55h"

echo "=== config: backup + point exe at 0.1.55h ==="
cp -f "$CFG" "$CFG.bak_w863_$TS"
echo "bak=$CFG.bak_w863_$TS"
python3 - "$CFG" <<'PY'
import json, sys
p = sys.argv[1]
d = json.load(open(p))
old = d.get('exe')
d['exe'] = '/data/bin/strata-0.1.55h'
json.dump(d, open(p, 'w'), indent=2, ensure_ascii=False)
print('exe:', old, '->', d['exe'])
print('env:', sorted(d.get('env', {}).items()))
PY
md5sum "$CFG"
