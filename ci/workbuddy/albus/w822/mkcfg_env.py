"""W822: 从（已换新权重的）生产配置派生 K-quant 专用实验配置。

用法: mkcfg_env.py <out.json> <logname> KEY=VAL [KEY=VAL ...]
只加/改 env，不动 args；log 指到独立文件，避免和生产日志混。
"""
import json
import sys

PROD = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"
out, logname = sys.argv[1], sys.argv[2]

d = json.load(open(PROD, encoding="utf-8"))
for kv in sys.argv[3:]:
    k, v = kv.split("=", 1)
    d.setdefault("env", {})[k] = v
d["log"] = "/data/%s.log" % logname
json.dump(d, open(out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

print("wrote", out, "env_n=%d args_n=%d log=%s" % (len(d["env"]), len(d["args"]), d["log"]))
print("--native:", d["args"][d["args"].index("--native") + 1].split("/")[-1])
print("--pack  :", d["args"][d["args"].index("--pack") + 1])
print("diff env:", {k: v for k, v in d["env"].items()})
