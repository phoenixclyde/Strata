r"""param_pair_lint.py —— 抓「同族参数只改了一半」的账本滞后。

由来（AUDIT21 B7 / AUDIT22）：`P23`（`STRATA_PREFILL_CPU_SHARE`）与 `P129`（`..._SHARE_MAX`）是同一族，
W804 把 MAX 从 1024 改判到 3072 时**改判只写进了 P129**，`P23` 的正文一直停在 W802 的
「值保持 0」，而生产实际是 `auto`。只看 P23 会误判 prefill 现状。

判据（机械，不猜语义；**只认同族**，不做全文互引，否则 234 条表会刷出 86 条噪声）：
  1. 族键 = 参数名去掉尾部 `_MAX/_MIN/_PCT/_GIB/_MIB/_SIZE/_COUNT/_N/_ENABLE/_MS`，再与另一行比较
     —— 两者族键相同、或一方是另一方的前缀，即视为同族；
  2. 较晚者（B）证据里最晚的 W 号 > 较早者（A）的；
  3. A 正文里**没出现**那个更晚的 W 号（= 没有指针过去）；
  ⇒ 报「A 被 B 的改判覆盖，但 A 无指针」。

用法: python tools/param_pair_lint.py [--quiet] [--strict]
退出码: 默认 0（提示性）；--strict 时有命中返回 1。
"""
from __future__ import annotations

import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = os.path.join(ROOT, "deploy", "params", "PARAM_REGISTER.tsv")

RX_W = re.compile(r"\bW(\d{3})\b")
SUFFIX = re.compile(r"_(MAX|MIN|PCT|GIB|MIB|SIZE|COUNT|N|ENABLE|MS)$")


RX_TOK = re.compile(r"(--[a-z][a-z0-9-]+|STRATA_[A-Z0-9_]+)")
RX_VERDICT = re.compile(r"(改判|更正|替代|取代|升级为|回退|推翻|撤销判决)")


def fam(name: str) -> str:
    """族键：名字里第一个完整的开关/环境变量 token，去掉尾部量纲后缀。

    用完整 token 而不是 split()[0]，否则 `--spec` 与 `--spec-min-p` 会被当成同族（实测刷出 86 条噪声）。
    """
    m = RX_TOK.search(name)
    if not m:
        return ""
    return SUFFIX.sub("", m.group(1))


def load():
    rows = {}
    for ln in io.open(REG, encoding="utf-8", errors="replace"):
        f = ln.rstrip("\n").split("\t")
        if len(f) < 6 or not f[0].startswith("P"):
            continue
        body = "\t".join(f[2:])
        ws = [int(x) for x in RX_W.findall(body)]
        rows[f[0]] = {
            "name": f[2][:56],
            "status": f[5],
            "fam": fam(f[2]),
            "ws": ws,
            "max_w": max(ws) if ws else 0,
            "body": body,
        }
    return rows


def main(argv):
    quiet = "--quiet" in argv
    strict = "--strict" in argv
    rows = load()

    by_fam = {}
    for pid, r in rows.items():
        # 证据里一个 W 号都没有的行判不了「谁更新」，直接跳过
        if r["fam"] and len(r["fam"]) >= 6 and r["max_w"] > 0:
            by_fam.setdefault(r["fam"], []).append(pid)

    hits = []
    for key, ids in by_fam.items():
        if len(ids) < 2:
            continue
        ids.sort(key=lambda p: rows[p]["max_w"])
        for i, a_id in enumerate(ids):
            a = rows[a_id]
            for b_id in ids[i + 1:]:
                b = rows[b_id]
                if b["max_w"] <= a["max_w"]:
                    continue
                # 只有「判决性」的更晚证据才算数：正文里必须出现改判/更正/替代这类词。
                # 否则任何一句顺带提及都会触发（实测宽判据刷出 86 条噪声）。
                if not RX_VERDICT.search(b["body"]):
                    continue
                later = [w for w in b["ws"] if w > a["max_w"]]
                if not later:
                    continue
                if any(("W%d" % w) in a["body"] for w in later):
                    continue
                hits.append((key, a_id, a["name"], a["status"], a["max_w"],
                             b_id, b["status"], max(later)))

    if not quiet:
        print("登记表 %d 条 / 同族组 %d 个；族内滞后 %d 处"
              % (len(rows), sum(1 for v in by_fam.values() if len(v) > 1), len(hits)))
        for key, a_id, a_name, a_st, a_w, b_id, b_st, w in hits:
            print("  [%s] %-5s %-40s [%s] 最晚 W%d" % (key[:18], a_id, a_name, a_st, a_w))
            print("        ↑ 同族 %s [%s] 在 W%d 有更晚判决，而 %s 正文没提到它" % (b_id, b_st, w, a_id))
    if hits:
        print("\n**param-pair-lint：%d 处族内滞后**（处置：给前面的那行加一句指针即可，不必改结论）" % len(hits))
        return 1 if strict else 0
    print("\n**param-pair-lint PASS：同族参数没有被后行改判却无指针的情况**")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
