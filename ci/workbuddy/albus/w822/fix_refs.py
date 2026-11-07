"""W822: 修掉配置里指向旧权重的两处非 args 引用（生产文件原地改，先备份）。

  tokenizer        : /data/packs/huihui-ud-iq4_xs/tokenizer -> /data/packs/ud-q4_k_xl/tokenizer
  vision.model     : .../unsloth-UD-IQ4_XS/...-00001-of-00003.gguf
                     -> .../unsloth-UD-Q4_K_XL/...-00001-of-00004.gguf
model_name 不动（它是 OpenAI 侧的 model id，改了就断现有客户端）。
"""
import json
import os
import shutil

P = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"
NEW_TOK = "/data/packs/ud-q4_k_xl/tokenizer"
NEW_MODEL = ("/models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/unsloth-UD-Q4_K_XL/"
             "Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf")

shutil.copyfile(P, P + ".w822_bak2")
d = json.load(open(P, encoding="utf-8"))

print("tokenizer :", d["tokenizer"], "->", NEW_TOK)
d["tokenizer"] = NEW_TOK

old_v = d["vision"]["model"]
print("vision    :", old_v.split("/")[-2] + "/" + old_v.split("/")[-1])
d["vision"]["model"] = NEW_MODEL
print("           ->", NEW_MODEL.split("/")[-2] + "/" + NEW_MODEL.split("/")[-1])

tmp = P + ".tmp"
json.dump(d, open(tmp, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
os.replace(tmp, P)

# 自检：配置里不该再出现旧权重名
blob = open(P, encoding="utf-8").read()
bad = [s for s in ("huihui-ud-iq4_xs/", "UD-IQ4_XS", "iq4_xs/tokenizer") if s in blob]
print("残留旧引用:", bad if bad else "无")
