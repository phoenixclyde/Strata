#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""recipe_check -- 装机件必须能由「仓库 sha + llama 版本 + 构建目录」重建。

W1037 起因（机主：「你的门又有问题了吧。你自己看看什么丢了」）：
`/data/bin/strata-0.1.57-010`（K10）在，它的源树没了。deploy_gate 的 D2 只查「有回滚件」、
D6 只查「有报告」，**没有一条门要求「这个二进制能再编出来」**。于是「不可重建」可以静默存在，
直到下一次想跟上游对齐时才发现无路可走。

判据（fail-closed）：
  * 每行 8 列；`LOST` 是**唯一**允许的"不可重建"标记，且必须带一个 `P<数字>` 编号（缺口已登记）；
  * 非 LOST 的行，`repo_sha` / `llama_base` / `llama_mmq` / `build_dir` 四列都不得为空或写「未记录」；
  * `--live` 时额外核 `/data/bin` 里这些件是否存在、md5 是否与表一致（只读）。

用法: python tools/recipe_check.py [--live]
"""
import io
import os
import re
import subprocess
import sys

TSV = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "deploy", "REBUILD_RECIPE.tsv")
COLS = ["exe", "md5", "size_B", "repo_sha", "llama_base", "llama_mmq", "build_dir", "note"]
BAD = ("未记录", "UNKNOWN", "")


def main():
    live = "--live" in sys.argv
    rows, fails = [], []
    for i, ln in enumerate(io.open(TSV, encoding="utf-8").read().splitlines(), 1):
        ln = ln.lstrip("﻿")
        if not ln.strip() or ln.lstrip().startswith("#"):
            continue
        f = ln.split("\t")
        if len(f) != len(COLS):
            fails.append("行 %d：%d 列（要 %d）" % (i, len(f), len(COLS)))
            continue
        r = dict(zip(COLS, f))
        rows.append(r)
        lost = "LOST" in r["build_dir"]
        if lost:
            if not re.search(r"P\d+", r["note"]):
                fails.append("%s：LOST 但没登记编号（note 里要有 P<数字>）" % r["exe"])
            continue
        for c in ("repo_sha", "llama_base", "llama_mmq", "build_dir"):
            if any(b and b in r[c] for b in BAD):
                fails.append("%s：%s 为空或写「未记录」⇒ 不可重建" % (r["exe"], c))
        if not re.fullmatch(r"[0-9a-f]{32}", r["md5"]):
            fails.append("%s：md5 不是 32 位 hex" % r["exe"])

    lost = [r["exe"] for r in rows if "LOST" in r["build_dir"]]
    print("RECIPE: %d 行（其中登记在案的不可重建 %d 件：%s）" % (len(rows), len(lost), ", ".join(lost) or "无"))
    if live:
        for r in rows:
            if not re.fullmatch(r"[\w.\-]+", r["exe"]):
                continue
            if "未装机" in r["note"]:
                print("  [skip] %-24s 未装机" % r["exe"])
                continue
            cmd = "md5sum /home/albus/strata166/data/bin/%s 2>/dev/null | cut -d' ' -f1" % r["exe"]
            p = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
                                "albus@192.168.50.166", cmd], capture_output=True, text=True)
            got = (p.stdout or "").strip()
            if not got:
                fails.append("%s：/data/bin 里没有这个文件（live）" % r["exe"])
            elif re.fullmatch(r"[0-9a-f]{32}", r["md5"]) and got != r["md5"]:
                fails.append("%s：live md5 %s != 表 %s" % (r["exe"], got[:12], r["md5"][:12]))
            else:
                print("  [ok ] %-24s md5=%s" % (r["exe"], got[:12]))

    if fails:
        for x in fails:
            print("  [FAIL] " + x)
        print("RECIPE_CHECK: FAIL (%d)" % len(fails))
        return 1
    print("RECIPE_CHECK: PASS（每件在产的都可重建；不可重建的已登记编号）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
