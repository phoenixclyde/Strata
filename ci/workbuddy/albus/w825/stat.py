import json, subprocess, os

CFG = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"
d = json.load(open(CFG))
print("  exe     :", d["exe"])
print("  model   :", d.get("model_name"))
print("  env_n   :", len(d["env"]), " args_n:", len(d["args"]))
print("  --- env ---")
for k, v in sorted(d["env"].items()):
    print("    %-34s %s" % (k, v))

print("  --- 关键 args ---")
a = d["args"]
for flag in ("--pack", "--native", "--spec", "--spec-min-p", "--pcie-frac",
             "--expert-cache", "--kv", "--prefill", "--mtp", "--prefill-cpu-cache-mib"):
    if flag in a:
        i = a.index(flag)
        print("    %-22s %s" % (flag, str(a[i + 1])[:110]))
