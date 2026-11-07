#!/bin/bash
set -u
cd /home/albus/strata166/pr/strata-fork
git add ci/cfg_apply.py
git -c user.name=strata -c user.email=strata@local commit -q -m "cfg_apply: --unset-env / --unset-arg (removing a dead knob is a change like any other)

The audit found a registered-dead env (STRATA_RESIDENT_HEADROOM_GIB, P65: 'configured but
inert') still in production, and --pcie-frac blocking the pcie_frac_auto candidate. Removing
either must go through the same gate as adding one."

echo "===== A) 删死参 STRATA_RESIDENT_HEADROOM_GIB（--force-keep，清理不是实验）====="
python3 ci/cfg_apply.py --label w986-del-headroom --unset-env STRATA_RESIDENT_HEADROOM_GIB --force-keep --n 10 --apply 2>&1 | tail -8

echo
echo "===== B) P227 解锁：去 --pcie-frac + STRATA_PCIE_FRAC_DEFAULT=auto ====="
python3 ci/cfg_apply.py --label w986-pcie-auto --unset-arg pcie-frac --env STRATA_PCIE_FRAC_DEFAULT=auto --baseline w986-del-headroom --n 10 --apply 2>&1 | tail -9

echo
echo "===== 终态 ====="
python3 - <<'PY'
import json
c=json.load(open("/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"))
a=c["args"]
print(" args",len(a),"| pcie-frac:", a[a.index("--pcie-frac")+1] if "--pcie-frac" in a else "(absent)",
      "| env",type(c["env"]).__name__,len(c["env"]),
      "| headroom:", "STRATA_RESIDENT_HEADROOM_GIB" in c["env"],
      "| pcie-env:", c["env"].get("STRATA_PCIE_FRAC_DEFAULT"))
PY
curl -s -m 3 localhost:8090/health | head -c 60; echo
