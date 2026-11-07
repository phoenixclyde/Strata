"""W822: 把「换权重」的三处改动写进生产配置（原子替换；备份已在 w822_prod_backup.json）。

只改 args 里的三项：
  --pack / --native / --expert-profile-save
env 与其余参数逐字不动；log 保持生产原路径。
"""
import json
import os

PROD = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"
SRC = "/home/albus/strata166/data/w822_q4kxl.json"

prod = json.load(open(PROD, encoding="utf-8"))
src = json.load(open(SRC, encoding="utf-8"))

for flag in ("--pack", "--native", "--expert-profile-save"):
    i = prod["args"].index(flag)
    j = src["args"].index(flag)
    old = prod["args"][i + 1]
    prod["args"][i + 1] = src["args"][j + 1]
    print("%-22s %s\n%22s -> %s" % (flag, old.split("/")[-1], "", prod["args"][i + 1].split("/")[-1]))

# 断言：env 必须与备份一致（只换权重，不动参数）
bak = json.load(open("/home/albus/strata166/data/w822_prod_backup.json", encoding="utf-8"))
assert prod["env"] == bak["env"], "env changed!"
assert len(prod["args"]) == len(bak["args"]), "args count changed!"
assert prod["log"] == bak["log"], "log path changed!"

tmp = PROD + ".tmp"
json.dump(prod, open(tmp, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
os.replace(tmp, PROD)
print("written", PROD)
print("env_n=%d args_n=%d log=%s" % (len(prod["env"]), len(prod["args"]), prod["log"]))
