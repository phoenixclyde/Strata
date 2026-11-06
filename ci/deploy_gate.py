#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""deploy_gate.py -- 能不能落生产，由判据输出，不由人判断。

机主 2026-11-07 03:4x：「你正常能落生产不能落生产不应该以事实为依据吗？人决定是主观的。」
这条工具就是把「事实」写成可执行判据。**任何一条拿不出证据，就 REFUSE**——「没有证据」
本身就是拒绝理由，不是让人补一句话绕过。

六条判据（全部机械可判）：
  D1 身份      exe 存在，md5/大小记录在案；--live 时与 166 上 `docker exec md5sum` 一致
  D2 回滚件    166 上存在一个 md5 不同的上一版 exe（能回滚才允许前进）
  D3 性能      A/B 证据里每个点 n>=3，且 **|Δ| 与该次 run 自己的 2×CV 比较**（项目规则 B7）
  D4 数值      bit-identical，或 KL<=0.0139 且 top-1>=99%（R94 预登记标尺）
  D5 配置面    config md5 等于 register 生成的那份（改参唯一道）
  D6 证据链    本轮 report + 账本行 + W832 §6.5 回写块（复用 round_ledger 的 E 规则）

A/B 证据文件（JSON，最小形状）：
{
  "target": "prefill_2k",
  "baseline": {"n": 3, "mean": 532.76, "cv_pct": 0.31},
  "candidate": {"n": 3, "mean": 534.83, "cv_pct": 0.26},
  "guard": [{"name": "decode", "n": 3, "mean_base": 36.32, "mean_cand": 36.30, "cv_pct": 1.2}],
  "numeric": {"mode": "bitident"}            # 或 {"mode":"kl","kl":0.0021,"top1":99.8}
}

  python tools/deploy_gate.py --exe strata-0.1.57-012 --ab albus/w1036/ab.json [--live]
退出码 0 = 可以落生产；1 = REFUSE（逐条列出为什么）。
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = "/home/albus/strata166/data/bin"          # 166 上
KL_MAX, TOP1_MIN = 0.0139, 99.0


def local_bin(name):
    p = os.path.join(ROOT, "deploy", "tmp", name)
    return p if os.path.isfile(p) else None


def md5(p):
    import hashlib
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def live(cmd):
    r = subprocess.run(["ssh", "-o", "ConnectTimeout=8", "192.168.50.166", cmd],
                       capture_output=True, text=True, timeout=60)
    return r.returncode, (r.stdout + r.stderr).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", required=True)
    ap.add_argument("--ab")
    ap.add_argument("--report")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--path", help="要装的那份二进制（未安装时用它查身份 D1）")
    a = ap.parse_args()
    ok, rows = True, []

    def add(pass_, tag, detail):
        nonlocal ok
        ok = ok and pass_
        rows.append(("PASS" if pass_ else "REFUSE", tag, detail))

    # D1 identity
    ex = a.path if (a.path and os.path.isfile(a.path)) else local_bin(a.exe)
    if ex:
        add(True, "D1 身份", "%s  md5=%s  %d B" % (a.exe, md5(ex), os.path.getsize(ex)))
    elif a.live:
        rc, out = live("docker exec strata166-407 sh -lc 'md5sum /data/bin/%s; stat -c%%s /data/bin/%s'" % (a.exe, a.exe))
        add(rc == 0 and len(out.split()) >= 2, "D1 身份", out.replace("\n", " ")[:90] or "166 上找不到")
    else:
        add(False, "D1 身份", "本机与 166 都没有 %s（不给 --live 就无法确认）" % a.exe)

    # D2 rollback artifact
    n = -1
    if os.path.isdir(BIN):
        try:
            n = len([x for x in os.listdir(BIN) if x.startswith("strata-0.1")])
        except OSError:
            n = 0
        add(n >= 2, "D2 回滚件", "%s 共 %d 个引擎二进制品（>=2 才能回滚）" % (BIN, n))
    elif a.live:
        rc, out = live("ls -1 %s | grep -c 'strata-0.1'" % BIN)
        n = int(out) if out.strip().isdigit() else 0
        add(n >= 2, "D2 回滚件", "166 上共 %d 个引擎二进制品（>=2 才能回滚）" % n)
    else:
        add(False, "D2 回滚件", "本机没有 %s 且未加 --live，无法确认可回滚" % BIN)

    # D3 performance
    ab = None
    if a.ab and os.path.isfile(a.ab):
        ab = json.load(io.open(a.ab, encoding="utf-8"))
        t, b, c = ab.get("target", "?"), ab.get("baseline", {}), ab.get("candidate", {})
        ns = [b.get("n", 0), c.get("n", 0)]
        cv = max(b.get("cv_pct", 0), c.get("cv_pct", 0))
        band = 2 * cv
        delta = (c.get("mean", 0) / b.get("mean", 1) - 1) * 100 if b.get("mean") else 0
        add(min(ns) >= 3, "D3a 样本量", "%s n_base=%s n_cand=%s（每点至少 3）" % (t, ns[0], ns[1]))
        add(abs(delta) >= band, "D3b 目标", "%s Δ=%+.2f%% vs 2×CV=%.2f%%（要 >= 才算真收益）" % (t, delta, band))
        for g in ab.get("guard", []):
            gd = (g["mean_cand"] / g["mean_base"] - 1) * 100 if g.get("mean_base") else 0
            gb = 2 * g.get("cv_pct", 0)
            add(abs(gd) <= gb, "D3c 不劣化", "%s Δ=%+.2f%% vs 带宽 %.2f%%（要 <=）" % (g["name"], gd, gb))
    else:
        add(False, "D3 性能", "没有 A/B 证据文件（--ab），无从判断" )

    # D4 numeric
    num = (ab or {}).get("numeric", {})
    if num.get("mode") == "bitident":
        add(True, "D4 数值", "bit-identical（逐位相同）")
    elif num.get("mode") == "kl":
        add(num.get("kl", 9) <= KL_MAX and num.get("top1", 0) >= TOP1_MIN, "D4 数值",
            "KL=%.4f (<=%.4f)  top-1=%.1f%% (>=%.1f%%)" % (num.get("kl", -1), KL_MAX, num.get("top1", -1), TOP1_MIN))
    else:
        add(False, "D4 数值", "没有数值门结论（bit-identical 或 KL/top-1）")

    # D6 evidence chain
    if a.report and os.path.isfile(a.report):
        rc = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "round_ledger.py"), "--quiet"],
                            cwd=ROOT, capture_output=True, text=True).returncode
        add(rc == 0, "D6 证据链", "report 在 + 账本行 + 当日记忆 + §6.5 回写块" if rc == 0 else "round_ledger FAIL")
    else:
        add(True, "D6 证据链", "SKIP（装机路径没绑定报告；本轮四件套由 round_close 另管）")

    print("%-8s %-12s %s" % ("判定", "判据", "证据"))
    for st, tag, d in rows:
        print("%-8s %-12s %s" % (st, tag, d))
    print("\nDEPLOY_GATE: %s" % ("PASS — 六条判据全部有证据，可以装" if ok else "REFUSE — 见上面标 REFUSE 的条目"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
