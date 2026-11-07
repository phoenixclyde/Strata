import json
p = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"
d = json.load(open(p))
e = d["env"]
a = d["args"]
print("env_n=%d args_n=%d" % (len(e), len(a)))
print("unbuffered=" + str(e.get("STRATA_UNBUFFERED_LOAD", "-")))
print("ple_args=" + str([k for k in a if "ple" in k] or "NONE"))
print("prefill=" + str(a[a.index("--prefill") + 1]))
print("timing=" + str([k for k in e if "TIMING" in k or "TRACE" in k] or "NONE"))
print("env_keys=" + ",".join(sorted(e)))
