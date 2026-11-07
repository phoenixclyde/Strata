#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""binary_integrity -- disk md5 == running-process md5 == SNAPSHOT prod_md5.

W1045: `llvm-objcopy --dump-section` with no output argument rewrote the LIVE
binary in place. The old handoff_check only compared disk md5 to the SNAPSHOT,
not to the bytes the running engine actually holds, so a deleted-inode process
plus a damaged disk file could stay green until the next restart.

    python tools/binary_integrity.py --live       # read-only check against 166
    python tools/binary_integrity.py --self-test  # negative cases
"""
import io
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SNAP = os.path.join(ROOT, "albus", "w1034", "HANDOFF.md")
sys.path.insert(0, os.path.join(ROOT, "deploy", "params"))
import _sshutil  # noqa: E402


def snapshot():
    m = re.search(r"> SNAPSHOT:.*?prod_exe=(\S+).*?prod_md5=([0-9a-f]{32})",
                  io.open(SNAP, encoding="utf-8").read())
    return (m.group(1), m.group(2)) if m else (None, None)


def live_facts(exe):
    name = exe.rsplit("/", 1)[-1]
    cmd = ("C=strata166-407; "
           "echo DISK=$(docker exec $C md5sum /data/bin/%s 2>/dev/null | cut -d' ' -f1); "
           "echo RUNNING=$(docker exec $C sh -lc 'for p in $(pgrep -x strata-host | head -1); "
           "do md5sum /proc/$p/exe; done' 2>/dev/null | cut -d' ' -f1); "
           "echo EXEPATH=$(docker exec $C sh -lc 'for p in $(pgrep -x strata-host | head -1); "
           "do readlink /proc/$p/exe; done' 2>/dev/null)") % name
    rc, out, err = _sshutil.run_remote(cmd, timeout=120)
    d = {}
    for line in out.splitlines():
        if line.startswith(("DISK=", "RUNNING=", "EXEPATH=")):
            k, _, v = line.partition("=")
            d[k] = v.strip()
    return d


def verdict(exe, want, facts):
    problems = []
    disk, running = facts.get("DISK"), facts.get("RUNNING")
    if not disk:
        problems.append("磁盘件 md5 读不到")
    if not running:
        problems.append("运行进程 /proc/<pid>/exe md5 读不到")
    if disk and want and disk != want:
        problems.append("disk %s != SNAPSHOT %s" % (disk[:12], want[:12]))
    if running and want and running != want:
        problems.append("running %s != SNAPSHOT %s" % (running[:12], want[:12]))
    if disk and running and disk != running:
        problems.append("disk != running（重启会静默换件，W940/W1045 同款）")
    warn = []
    if facts.get("EXEPATH", "").endswith("(deleted)"):
        # Content-equal inode swap is NOT a version change. W940's rule is md5,
        # not inode. Report it, but do not fail a healthy production box.
        warn.append("运行进程持有已删除 inode（内容一致，重启不会换版本）：%s" % facts["EXEPATH"])
    return problems, warn


def main():
    exe, want = snapshot()
    if "--self-test" in sys.argv:
        base = {"DISK": want, "RUNNING": want, "EXEPATH": "/data/bin/" + exe}
        cases = [
            ("三方一致", base, 0, 0),
            ("磁盘件被改", dict(base, DISK="0" * 32), 2, 0),
            ("运行件被换", dict(base, RUNNING="1" * 32), 2, 0),
            ("deleted inode 仅警告", dict(base, EXEPATH=base["EXEPATH"] + " (deleted)"), 0, 1),
            ("两边都读不到", {"DISK": "", "RUNNING": ""}, 2, 0),
        ]
        bad = 0
        for name, facts, wantp, wantw in cases:
            p, w = verdict(exe, want, facts)
            ok = len(p) == wantp and len(w) == wantw
            bad += 0 if ok else 1
            print("  %-22s %-4s problems=%d warnings=%d" % (name, "PASS" if ok else "FAIL", len(p), len(w)))
        print("BINARY_INTEGRITY_SELF_TEST: %d/%d" % (len(cases) - bad, len(cases)))
        return 1 if bad else 0
    facts = live_facts(exe)
    p, w = verdict(exe, want, facts)
    print("SNAPSHOT prod_exe=%s prod_md5=%s" % (exe, want))
    for k in ("DISK", "RUNNING", "EXEPATH"):
        print("  %-8s %s" % (k, facts.get(k)))
    if p:
        print("BINARY_INTEGRITY: FAIL")
        for x in p:
            print("  -", x)
        return 1
    for x in w:
        print("  WARN", x)
    print("BINARY_INTEGRITY: PASS (disk = running = SNAPSHOT，按 md5 而非 inode)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
