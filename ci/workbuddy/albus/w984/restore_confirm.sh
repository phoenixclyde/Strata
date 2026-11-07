#!/bin/bash
set -u
cd /home/albus/strata166/pr/strata-fork
echo "===== 1) 恢复已知good值 pcie-frac=0.20（强制保留，不当作实验）====="
python3 ci/cfg_apply.py --label restore-pcie020 --set pcie-frac=0.20 --force-keep --n 3 --apply 2>&1 | tail -6
echo
echo "===== 2) 0.35 复核（n=10，对照 p4-base3）====="
python3 ci/cfg_apply.py --label p4d4-pciefrac035-n10 --set pcie-frac=0.35 --baseline p4-base3 --n 10 --apply 2>&1 | tail -8
echo
echo "===== 终态 ====="
python3 - <<'PY'
import json
c=json.load(open("/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"))
a=c["args"]
print(" pcie-frac =", a[a.index("--pcie-frac")+1], "| args", len(a), "| env", type(c["env"]).__name__, len(c["env"]))
PY
curl -s -m 3 localhost:8090/health | head -c 60; echo
