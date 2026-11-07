# -*- coding: utf-8 -*-
"""分析 rocprofv3 的 rocpd_*.db：按 kernel 聚合总耗时与调用次数。"""
import sqlite3, sys, os

P = sys.argv[1] if len(sys.argv) > 1 else "/home/albus/strata166/data/_prof/run_results.db"
TOP = int(sys.argv[2]) if len(sys.argv) > 2 else 30

c = sqlite3.connect(P)
tabs = [r[0] for r in c.execute("select name from sqlite_master where type='table'")]
def find(prefix):
    for t in tabs:
        if t.startswith(prefix):
            return t
    raise SystemExit("no table " + prefix)

kd = find("rocpd_kernel_dispatch")
ks = find("rocpd_info_kernel_symbol")

cols_kd = [r[1] for r in c.execute("pragma table_info(%s)" % kd)]
cols_ks = [r[1] for r in c.execute("pragma table_info(%s)" % ks)]
print("dispatch cols:", cols_kd)
print("symbol cols:", cols_ks)

# 找时间列与 kernel 关联列
print()
print("=== sample dispatch ===")
for r in c.execute("select * from %s limit 2" % kd):
    print(dict(zip(cols_kd, r)))
print()
print("=== sample symbol ===")
for r in c.execute("select * from %s limit 3" % ks):
    print(dict(zip(cols_ks, r)))
