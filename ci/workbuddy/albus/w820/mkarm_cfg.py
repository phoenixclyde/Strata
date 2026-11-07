"""W820: 由生产配置派生 A/B 三臂的配置（只改副本；生产文件只读）。

用法: mkarm_cfg.py <prod.json> <outdir>
产出:
  A.json  — 与生产逐字相同，仅 `log` 指向自己的文件（行为不变，日志独立）
  B.json  — A + `exe` 指向 0.1.52 + `STRATA_PLE_AUTO_RAM=0`
            （0.2.7 新增的默认会让引擎自己选 --ple-io ram；关掉它，A/B 才只差"引擎版本"这一个变量）
  A2.json — 与 A.json 内容相同（漂移检查用，名字不同只是为了让日志分开）
"""
import json
import os
import sys

prod, outdir = sys.argv[1], sys.argv[2]
V52 = "/opt/newbin/strata-0.1.52"
base = json.load(open(prod, encoding="utf-8"))
orig_exe = base["exe"]
os.makedirs(outdir, exist_ok=True)


def write(name, mut):
    d = json.loads(json.dumps(base))  # deep copy
    d["log"] = "/data/w820_%s.log" % name
    mut(d)
    p = os.path.join(outdir, "%s.json" % name)
    json.dump(d, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("%-5s exe=%-28s env_n=%2d args_n=%2d log=%s" % (name, d["exe"], len(d.get("env", {})), len(d["args"]), d["log"]))


def none(d):
    pass


def as_b(d):
    d["exe"] = V52
    d.setdefault("env", {})["STRATA_PLE_AUTO_RAM"] = "0"


write("A", none)
write("B", as_b)
write("A2", none)

# 自检：A 与 A2 必须逐字相同（除 log），生产文件未被写
a = json.load(open(os.path.join(outdir, "A.json"), encoding="utf-8"))
a2 = json.load(open(os.path.join(outdir, "A2.json"), encoding="utf-8"))
a.pop("log")
a2.pop("log")
assert a == a2, "A and A2 differ"
assert json.load(open(prod, encoding="utf-8"))["exe"] == orig_exe, "production exe changed!"
print("A/A2 identical except log; production untouched (exe still %s)" % orig_exe)
