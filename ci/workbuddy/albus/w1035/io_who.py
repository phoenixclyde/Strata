#!/usr/bin/env python3
"""Who is reading the disk?  Read-only sampler: per-process block-read rate + disk counters.

  python3 io_who.py [seconds]        (default 10)

read_bytes  = bytes this process actually pulled from the block layer (page-cache misses)
rchar       = bytes it asked for through syscalls (includes page-cache hits)
A mmap'd file that stays in page cache shows rchar=0 and read_bytes=0; one that is being
re-faulted shows read_bytes > 0 with majflt rising.
"""
import os
import sys
import time


def proc_io(pid):
    d = {}
    try:
        with open("/proc/%d/io" % pid) as f:
            for line in f:
                k, _, v = line.partition(":")
                d[k] = int(v)
    except OSError:
        return None
    return d


def all_procs():
    out = {}
    for e in os.listdir("/proc"):
        if not e.isdigit():
            continue
        pid = int(e)
        d = proc_io(pid)
        if d is None:
            continue
        try:
            with open("/proc/%d/comm" % pid) as f:
                name = f.read().strip()
        except OSError:
            name = "?"
        out[pid] = (name, d)
    return out


def disks():
    out = {}
    with open("/proc/diskstats") as f:
        for line in f:
            p = line.split()
            name = p[2]
            if name.startswith(("loop", "ram", "dm-", "sr")):
                continue
            if name[-1].isdigit() and not name.startswith("nvme"):
                continue          # partitions of sda/sdb
            if name.startswith("nvme") and "p" in name.split("n")[-1]:
                continue          # nvme0n1p1
            out[name] = (int(p[5]) * 512, int(p[9]) * 512)   # sectors read/written -> bytes
    return out


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    a, d0 = all_procs(), disks()
    t0 = time.time()
    time.sleep(n)
    b, d1 = all_procs(), disks()
    dt = time.time() - t0
    print("window %.1f s" % dt)

    print("\n%-8s %-22s %12s %12s %8s" % ("pid", "comm", "read_KB/s", "rchar_KB/s", "majflt"))
    rows = []
    for pid, (name, cur) in b.items():
        old = a.get(pid)
        if old is None:
            continue
        rb = (cur.get("read_bytes", 0) - old[1].get("read_bytes", 0)) / dt / 1024
        rc = (cur.get("rchar", 0) - old[1].get("rchar", 0)) / dt / 1024
        mf = cur.get("majflt", 0) - old[1].get("majflt", 0)
        if rb > 0.5 or rc > 0.5 or mf > 0:
            rows.append((rb, rc, mf, pid, name))
    for rb, rc, mf, pid, name in sorted(rows, reverse=True)[:12]:
        print("%-8d %-22s %12.1f %12.1f %8d" % (pid, name, rb, rc, mf))
    if not rows:
        print("  (no process read anything measurable)")

    print("\n%-12s %12s %12s" % ("disk", "read_KB/s", "write_KB/s"))
    for name, (r, w) in sorted(d1.items()):
        if name not in d0:
            continue
        rr = (r - d0[name][0]) / dt / 1024
        ww = (w - d0[name][1]) / dt / 1024
        if rr > 0.5 or ww > 0.5:
            print("%-12s %12.1f %12.1f" % (name, rr, ww))

    eng = os.popen("pgrep -f '^/data/bin/strata-0\\.1' | head -1").read().strip()
    if eng.isdigit():
        pid = int(eng)
        print("\nengine pid %d" % pid)
        try:
            print(open("/proc/%d/smaps_rollup" % pid).read().strip()[:600])
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
