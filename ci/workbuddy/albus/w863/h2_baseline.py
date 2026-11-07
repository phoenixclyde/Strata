# -*- coding: utf-8 -*-
"""把 PROD_BASELINE.tsv 推进到本轮已汇报的状态（语义见文件头：汇报完再推进）。"""
import io
import shutil

P = r"D:\workbuddy_space\strata_ws\deploy\PROD_BASELINE.tsv"
shutil.copy2(P, P + ".w863bak")

new = {
    "commit": "f8bfcd6d0a90abe80627fdf774548877c7e9b653",   # 引擎 0.1.55h 就是从这棵树的代码编的
    "branch": "gfx906/mi50 (tip df326f9e; 唯一差别是 docs/DOWNSTREAM.md)",
    "tree": "79ab5c0c",
    "upstream": "c62d5e3a15 (v0.2.9)",
    "exe": "/data/bin/strata-0.1.55h",
    "exe_md5": "9a2ff8742f9918f657a468a7baeb177c",
    "cfg_md5": "2fd30a353dd4b728d1a949bedc3a91eb",
    "started": "2026-11-01T07:40:37.460756158Z",
}

lines = io.open(P, encoding="utf-8").read().split("\n")
out = []
for ln in lines:
    k = ln.split("\t")[0]
    if k in new and not ln.startswith("#"):
        out.append("%s\t%s" % (k, new[k]))
    else:
        out.append(ln)

# 追加一行说明本轮落产内容
note = ("# 2026-11-01 16:2x 推进：本轮落产 = 引擎 0.1.55g -> 0.1.55h（W863 R 表实测版 + STRATA_MMVQ_WAVE_ROWS 真读），"
        "同镜像 A/B +4.0%；镜像未变（/data 是 bind mount，镜像不带运行中的引擎）；config 只改 exe 一个字段")
if not any("2026-11-01 16:2x 推进" in ln for ln in out):
    out.insert(1, note)

io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(out))

for ln in io.open(P, encoding="utf-8").read().split("\n")[:16]:
    print(ln[:120])
