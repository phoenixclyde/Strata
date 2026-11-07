"""W820: 由生产配置派生实验配置（不改生产那份）。

用法: mkcfg.py <src.json> <dst.json> <extra-arg>[,<extra-arg>...]
"""
import json
import sys

src, dst, extra = sys.argv[1], sys.argv[2], sys.argv[3]
d = json.load(open(src, encoding="utf-8"))
d["args"] = list(d["args"]) + extra.split(",")
json.dump(d, open(dst, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print("wrote", dst, "args_n=", len(d["args"]), "tail=", d["args"][-3:])
