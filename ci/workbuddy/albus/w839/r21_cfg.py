#!/usr/bin/env python3
# W839-21 生成两臂配置：A=现役14env(n3)  B=TUNED+5 个非架构 env
import json, io, sys

SRC = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"
base = json.load(io.open(SRC, encoding="utf-8"))
print("prod keys:", sorted(base.keys()))
print("prod env :", sorted((base.get("env") or {}).keys()))
print("prod exe :", base.get("exe"), "| log:", base.get("log"))

PROD_ENV = dict(base.get("env") or {})
NON_ARCH = ["HSA_OVERRIDE_GFX_VERSION", "STRATA_PREFILL_CPU_SHARE", "STRATA_PREFILL_CPU_SHARE_MAX",
            "STRATA_RESIDENT_HEADROOM_GIB", "STRATA_ROCBLAS_TUNING"]
ARCH = [k for k in PROD_ENV if k not in NON_ARCH]
print("arch vars (%d): %s" % (len(ARCH), sorted(ARCH)))

def write(tag, env, log):
    c = json.loads(json.dumps(base))
    c["exe"] = "/data/bin/strata-0.1.54n3"
    c["log"] = log
    c["env"] = env
    p = "/home/albus/strata166/data/w839_%s.json" % tag
    io.open(p, "w", encoding="utf-8").write(json.dumps(c, ensure_ascii=False, indent=1))
    print("wrote", p, "env count", len(env))

a_env = dict(PROD_ENV); a_env["STRATA_DECODE_TIMING"] = "1"
write("A", a_env, "/data/w839_A.log")

b_env = {k: PROD_ENV[k] for k in NON_ARCH}
b_env["STRATA_GFX906_TUNED"] = "1"
b_env["STRATA_DECODE_TIMING"] = "1"
write("B", b_env, "/data/w839_B.log")
print("B env:", sorted(b_env))
