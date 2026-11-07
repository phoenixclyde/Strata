#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""report_depth.py -- the four-section report must carry content, not just the labels.

W1012 起因（机主："你的四项报告内容越来越少了"）：`report_lint.py` 只查字段**在不在**，于是
「3a args 明细 | 未变」也能过。实测 11 份报告：

    args 明细从 19 条 --flag 掉到 1 条（w1003 起），w1010 是 0；
    正文 file:line 引用从 18–27 处掉到 0–3 处；
    全文字数 5,147 → 2,428（腰斩）。

字段在、内容没了，是最难被自己发现的一类退化：门是绿的，读的人要凭记忆对比上一轮。所以这里把
「够不够」变成阈值，阈值取**早期达标报告的实测下限**，不凭空定：

  一、≥9 行；3a 行 ≥15 个 `--flag`；3b 行 ≥8 个 env 名；≥2 个 32 位 md5
  （三、的字段由 report_lint 管；这里不重复设词表）
  四、必须有「N 条 / 已结 M / P%」与 ≥6 个队列 ID
  正文 ≥1500 字符、≥4 处 `file.ext:line`、≥3 个带单位量化值 + ≥15 个数字事实

  python3 tools/report_depth.py <report.md> [more.md ...]
  python3 tools/report_depth.py --self-test <一份达标报告>
"""
import io
import re
import sys


def split_sections(s):
    """一 / 二 / 三 / 四 四个块，兼容 '**一、' 与 '## 一、' 两种写法。"""
    marks = []
    for n in "一二三四":
        i = s.find("**%s、" % n)
        j = s.find("## %s、" % n)
        marks.append(min([x for x in (i, j) if x >= 0] or [len(s)]))
    out = {}
    names = ["一", "二", "三", "四"]
    for k, n in enumerate(names):
        end = marks[k + 1] if k + 1 < len(names) else len(s)
        out[n] = s[marks[k]:end] if marks[k] < end else ""
    out["body"] = s[marks[3]:] if marks[3] < len(s) else ""
    return out


def check(path):
    s = io.open(path, encoding="utf-8").read()
    sec = split_sections(s)
    f = []

    s1 = sec["一"]
    rows = [l for l in s1.splitlines() if l.startswith("| ") and not set(l) <= set("|- ")]
    if len(rows) < 9:
        f.append("一、只有 %d 行（要 ≥9：8 字段 + 3a + 3b）" % len(rows))
    a3 = [l for l in s1.splitlines() if l.startswith("| 3a")]
    a3b = [l for l in s1.splitlines() if l.startswith("| 3b")]
    nflag = len(re.findall(r"`--[a-z]", a3[0])) if a3 else 0
    nenv = len(re.findall(r"`(?:STRATA_|HSA_)", a3b[0])) if a3b else 0
    if nflag < 15:
        f.append("3a args 明细只有 %d 个 --flag（要 ≥15；「未变」不算明细）" % nflag)
    if nenv < 8:
        f.append("3b env 明细只有 %d 个变量名（要 ≥8）" % nenv)
    if len(set(re.findall(r"\b[0-9a-f]{32}\b", s))) < 2:
        f.append("少于 2 个 32 位 md5（引擎与 config 各一个）")

    # 三、的字段由 report_lint 管（改动/重启/停机/回滚件/提交），这里只量「有没有内容」，
    # 不重复设词表 —— 否则会把历史上合格的报告判死，阈值就失去了参照。

    s4 = sec["四"]
    if not re.search(r"\d+\s*条.*已结\s*\d+.*\d+(?:\.\d)?%", s4):
        f.append("四、缺「N 条 / 已结 M / P%」")
    if len(re.findall(r"\bR\d{1,3}\b", s4)) < 6:
        f.append("四、队列 ID 少于 6 个")

    body = sec["body"]
    if len(body) < 1500:
        f.append("正文只有 %d 字符（要 ≥1500）" % len(body))
    cites = len(re.findall(r"\.(?:cpp|h|cu|hpp|py|tsv|md):\d+", body))
    if cites < 4:
        f.append("正文只有 %d 处 file:line 引用（要 ≥4）" % cites)
    # 量化事实：带单位的（%/ms/GiB/字符…）优先，但也接受「5,147 条」这种计数——
    # 本轮可能一行性能数据都没有，逼它凑 8 个 ms 只会写出假数字。
    units = len(re.findall(r"\d+(?:\.\d+)?\s*(?:%|×|ms|µs|GiB|MiB|tok|字符|处|层)", body))
    quant = len(re.findall(r"\d[\d,]*", body))
    if units < 3:
        f.append("正文只有 %d 个带单位的量化值（要 ≥3）" % units)
    if quant < 15:
        f.append("正文只有 %d 个数字事实（要 ≥15）" % quant)

    return f


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    bad = 0
    for p in argv:
        f = check(p)
        if f:
            bad += 1
            print("REPORT_DEPTH: FAIL %s (%d)" % (p, len(f)))
            for x in f:
                print("   - " + x)
        else:
            print("REPORT_DEPTH: PASS %s" % p)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
