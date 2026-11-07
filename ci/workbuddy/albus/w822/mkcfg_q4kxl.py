"""W822: 由生产配置派生「换权重到 UD-Q4_K_XL」的配置（生产文件只读）。

改动只有四处：
  --pack   /data/packs/huihui-ud-iq4_xs -> /data/packs/ud-q4_k_xl
  --native .../unsloth-UD-IQ4_XS/...-00001-of-00003.gguf
           -> .../unsloth-UD-Q4_K_XL/...-00001-of-00004.gguf
  --expert-profile-save 换个新文件（避免把旧权重的学习态混进来）
  log      -> /data/w822_q4kxl.log
其余 12 个 env 与所有其它参数逐字不动。
"""
import json
import shutil
import sys

PROD = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"
OUT = "/home/albus/strata166/data/w822_q4kxl.json"
BAK = "/home/albus/strata166/data/w822_prod_backup.json"

NEW_PACK = "/data/packs/ud-q4_k_xl"
NEW_NATIVE = ("/models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/unsloth-UD-Q4_K_XL/"
              "Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf")

d = json.load(open(PROD, encoding="utf-8"))
shutil.copyfile(PROD, BAK)  # 备份（生产文件本身不动）

args = list(d["args"])


def swap(flag, value):
    i = args.index(flag)
    old = args[i + 1]
    args[i + 1] = value
    return old


old_pack = swap("--pack", NEW_PACK)
old_native = swap("--native", NEW_NATIVE)
if "--expert-profile-save" in args:
    old_save = swap("--expert-profile-save", "/data/profiles/q4kxl-learned.bin")
else:
    old_save = "(none)"

d["args"] = args
d["log"] = "/data/w822_q4kxl.log"
json.dump(d, open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

print("backup   :", BAK)
print("new cfg  :", OUT)
print("pack     :", old_pack, "->", NEW_PACK)
print("native   :", old_native.split("/")[-1], "->", NEW_NATIVE.split("/")[-1])
print("save     :", old_save, "-> /data/profiles/q4kxl-learned.bin")
print("env_n=%d args_n=%d" % (len(d["env"]), len(d["args"])))
