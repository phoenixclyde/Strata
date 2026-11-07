# -*- coding: utf-8 -*-
"""按 kernel 聚合 rocprofv3 的结果：总忙时、调用次数、平均、grid/block、VGPR。"""
import sqlite3, sys

P = sys.argv[1] if len(sys.argv) > 1 else "/home/albus/strata166/data/_prof/run_results.db"
TOP = int(sys.argv[2]) if len(sys.argv) > 2 else 25

c = sqlite3.connect(P)
tabs = [r[0] for r in c.execute("select name from sqlite_master where type='table'")]
def find(pfx):
    for t in tabs:
        if t.startswith(pfx):
            return t
    raise SystemExit("no " + pfx)

kd, ks = find("rocpd_kernel_dispatch"), find("rocpd_info_kernel_symbol")

q = """
select s.kernel_name,
       s.display_name,
       count(*)                                   as n,
       sum(d."end" - d.start) / 1e6               as busy_ms,
       avg(d."end" - d.start) / 1e3               as avg_us,
       max(d.grid_size_x)                         as grid_x,
       max(d.workgroup_size_x)                    as blk,
       max(d.private_segment_size)                as priv,
       max(s.group_segment_size)                  as lds,
       max(s.arch_vgpr_count)                     as vgpr
from {kd} d join {ks} s on d.kernel_id = s.id
group by s.id
order by busy_ms desc
limit {top}
""".format(kd=kd, ks=ks, top=TOP)

rows = list(c.execute(q))
if not rows:
    raise SystemExit("no dispatches")

tot = c.execute('select (max("end") - min(start))/1e6, sum("end" - start)/1e6, count(*) from %s' % kd).fetchone()
print("span_ms=%.1f  busy_ms=%.1f  dispatches=%d  distinct_kernels=%d\n"
      % (tot[0], tot[1], tot[2], len(list(c.execute('select distinct kernel_id from %s' % kd)))))

print("%-46s %8s %10s %9s %7s %6s %6s %6s %6s" %
      ("kernel", "n", "busy_ms", "%busy", "avg_us", "grid_x", "blk", "priv", "vgpr"))
for r in rows:
    name = (r[1] or r[0] or "?")[:46]
    print("%-46s %8d %10.1f %8.1f%% %7.1f %6d %6d %6d %6d" %
          (name, r[2], r[3], 100.0 * r[3] / max(tot[1], 1e-9), r[4], r[5] or 0, r[6] or 0, r[7] or 0, r[8] or 0))
