#!/usr/bin/env python3
# W839-37 生产配置切换：n2+14env -> n3+6env(TUNED)。先备份。
import json, io, shutil, os

CFG = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"
BAK = CFG + ".bak-w839"
c = json.load(io.open(CFG, encoding="utf-8"))
if not os.path.exists(BAK):
    shutil.copy2(CFG, BAK)
    print("backup ->", BAK)
print("before: exe=%s env=%d" % (c["exe"], len(c["env"])))

KEEP = ["HSA_OVERRIDE_GFX_VERSION", "STRATA_PREFILL_CPU_SHARE", "STRATA_PREFILL_CPU_SHARE_MAX",
        "STRATA_RESIDENT_HEADROOM_GIB", "STRATA_ROCBLAS_TUNING"]
old = dict(c["env"])
missing = [k for k in KEEP if k not in old]
if missing:
    print("ABORT: missing non-arch env", missing); raise SystemExit(2)
dropped = [k for k in old if k not in KEEP]
print("dropped (%d): %s" % (len(dropped), sorted(dropped)))

c["exe"] = "/data/bin/strata-0.1.54n3"
c["env"] = {k: old[k] for k in KEEP}
c["env"]["STRATA_GFX906_TUNED"] = "1"
io.open(CFG, "w", encoding="utf-8").write(json.dumps(c, ensure_ascii=False, indent=1))
print("after : exe=%s env=%d %s" % (c["exe"], len(c["env"]), sorted(c["env"])))
