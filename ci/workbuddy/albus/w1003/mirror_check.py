#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mirror_check -- 权威件「本机主拷贝 ↔ 166 镜像」逐字节一致检定。

W1003 起因：机主问「本轮输出加到权威调优方案了吗」。查实没有；再查发现
`/home/albus/strata166/deploy/W832_OPT_PLAN_V2.md` 停在 2026-11-03 02:54
（98,538 B / 839 行），本机那份 132,894 B / 1,015 行 —— W882 之后 18 轮的
回写全在本机，166 那份「唯一排序处」冻结了两天，而 plan_lint 只读本机，
所以门一直绿。**这不是格式问题，是"权威件有两份、没人比对"的结构问题。**

W1004 扩展：权威件从两件变四件（+ params/PARAM_REGISTER.tsv、ID_MAP.tsv）。
W1006 再扩：审计索引与最新审计件（+ AUDIT_INDEX.md、AUDIT26_W898_W1005.md）——
索引过期就等于「哪些轮次没审」不可判，和 W832 那份冻结两天是同一个病。

W1037 再扩（机主：「你的门又有问题了吧。你自己看看什么丢了」）：
`albus/gfx906_survey/PORT_PLAN.md` 被机主在 2026-11-07 06:36 指定为「本方案的一个 R」，
**但它不在任何镜像集里，166 上根本没有这个文件** —— 一个被置顶的权威件只活在本机一块盘上，
是 W1003 那个病的第三次复发。本版把镜像从「deploy/ 下的六件」扩成
「deploy/ 六件 + 具名外部权威件」，外部件用 (本机路径, 远端名) 表示。

用法:
  python albus/w1003/mirror_check.py            # 只比对（round_close 里当硬门）
  python albus/w1003/mirror_check.py --sync     # 先推本机主拷贝再比对
  python albus/w1003/mirror_check.py --self-test # 负向自测：伪造漂移必须被判出
"""
import argparse
import hashlib
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HOST = "albus@192.168.50.166"
RDIR = "/home/albus/strata166/deploy"
# W1004：权威件是**四件**，此前只比两件 —— 2026-11-05 22:5x 实测 166 的
# params/PARAM_REGISTER.tsv 停在 2026-11-02 22:02、ID_MAP.tsv 根本不存在。
# 同一类缺陷（有两份、没人比）在参数册上又发生了一次。
# AUDIT27: "latest audit artefact" used to be a literal (AUDIT26).  Every new audit
# silently left 166 holding the previous one -- the exact two-copies disease this
# script exists to catch.  Derive it from the artefacts instead.
def latest_audit():
    import re
    best, name = -1, None
    for f in os.listdir(os.path.join(ROOT, "deploy")):
        m = re.match(r"^AUDIT(\d+)_.*\.md$", f)
        if m and int(m.group(1)) > best:
            best, name = int(m.group(1)), f
    assert name, "no AUDIT<number>_*.md found in deploy/"
    return name


FILES = ["W832_OPT_PLAN_V2.md", "PROGRESS.tsv", "params/PARAM_REGISTER.tsv", "ID_MAP.tsv",
         "AUDIT_INDEX.md", latest_audit()]

# W1037：deploy/ 之外的具名权威件。(本机相对路径, 166 上 deploy/ 里的文件名)
EXTRA = [
    ("albus/gfx906_survey/PORT_PLAN.md", "PORT_PLAN.md"),
]


def targets():
    return [(os.path.join("deploy", n), n) for n in FILES] + list(EXTRA)


def md5_local(rel):
    with open(os.path.join(ROOT, rel), "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def md5_remote():
    # 缺件也要能判：按件循环，不存在的跳过（比对时显示 missing），整体 rc 恒 0
    names = " ".join(n for _, n in targets())
    cmd = "cd %s && for f in %s; do [ -f $f ] && md5sum $f; done; true" % (RDIR, names)
    r = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", HOST, cmd],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ssh/md5sum failed: %s" % (r.stderr.strip() or r.returncode))
    out = {}
    for line in r.stdout.splitlines():
        p = line.split()
        if len(p) == 2:
            out[os.path.basename(p[1])] = p[0]
    return out


def push():
    for rel, name in targets():           # 逐件推：远端一律平铺进 deploy/
        src = os.path.join(ROOT, rel)
        base = os.path.basename(name)
        subprocess.run(["scp", "-q", src, "%s:/tmp/%s" % (HOST, base)], check=True)
        sub = os.path.dirname(name)
        if sub:
            subprocess.run(["ssh", HOST, "mkdir -p %s/%s" % (RDIR, sub)], check=True)
        cmd = ("cd %s && cp -n %s %s.bak_$(date +%%Y%%m%%d) 2>/dev/null; cp /tmp/%s %s"
               % (RDIR, name, name, base, name))
        r = subprocess.run(["ssh", HOST, cmd], capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError("push %s failed: %s" % (name, r.stderr.strip()))


def compare(remote):
    bad = []
    for rel, name in targets():
        a = md5_local(rel)
        b = remote.get(name) or remote.get(os.path.basename(name), "(missing)")
        flag = "ok " if a == b else "DRIFT"
        print("  [%s] %-24s local=%s remote=%s" % (flag, name, a[:12], b[:12]))
        if a != b:
            bad.append(name)
    return bad


def self_test():
    """伪造一份漂移的"远端哈希"，比对器必须判出。"""
    fake = {n: "0" * 32 for _, n in targets()}
    bad = compare(fake)
    ok = len(bad) == len(targets())
    print("  negative self-test: forged drift detected = %s (%d/%d)" % (ok, len(bad), len(targets())))
    print("MIRROR_CHECK: %s" % ("PASS" if ok else "FAIL (comparator blind)"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sync", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    try:
        if a.sync:
            push()
        bad = compare(md5_remote())
    except Exception as e:
        print("MIRROR_CHECK: FAIL (%s)" % e)
        return 1
    if bad:
        print("MIRROR_CHECK: FAIL (%s 与 166 不一致 ⇒ 先 --sync)" % ", ".join(bad))
        return 1
    print("MIRROR_CHECK: PASS (本机主拷贝 == 166 镜像，逐字节，%d 件)" % len(targets()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
