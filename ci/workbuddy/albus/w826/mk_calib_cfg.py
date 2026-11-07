# -*- coding: utf-8 -*-
"""明天 P0 用：生成 calibrate 的副本配置（不碰生产），并做准入检查。

calibrate.py 会自己 start_engine 并**写回配置**，所以：
  - 只给它副本
  - log 指向独立文件，免得污染生产日志
  - 生成后立刻记下生产指纹，收工时比对
"""
import json, os, shutil, hashlib

PROD = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"
DST = "/home/albus/strata166/data/w826_calib.json"
BAK = "/home/albus/strata166/data/w826_calib_orig.json"

md5 = lambda p: hashlib.md5(open(p, "rb").read()).hexdigest()
before = md5(PROD)

d = json.load(open(PROD))
d["log"] = "/data/w826_calib.log"          # 独立日志，不污染生产
json.dump(d, open(DST, "w"), indent=2, ensure_ascii=False)
shutil.copyfile(DST, BAK)                   # calibrate 会改它，留原件

after = md5(PROD)
print("prod md5 before =", before)
print("prod md5 after  =", after, "  <== 必须相同")
assert before == after, "生产配置被动了！"

print("copy written    =", DST)
print("  exe           =", d["exe"])
print("  env_n/args_n  =", len(d["env"]), "/", len(d["args"]))
print("  log           =", d["log"])
