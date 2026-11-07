# -*- coding: utf-8 -*-
"""收尾：删 _z_rk81 的 165 个文件（分批 50，只删文件，不碰目录）。
   前置：逐文件校验 源 ⊆ waves/（_gh.py 走白名单，其快照必须已在 tools/snapshots_premigrate/）。
"""
import hashlib, os, time

SRC = r"D:\workbuddy\_z_rk81"
DST = r"D:\workbuddy_space\strata_ws\waves"
SNAP = r"D:\workbuddy_space\strata_ws\tools\snapshots_premigrate\_z_rk81\_gh.py"
WL = {"_gh.py": "84e9897ec4e515c31b13b53ecd0a064f"}   # 源件 md5（迁移时有意改过 TOKF）
LOG = r"D:\workbuddy_space\strata_ws\tools\_delete_manifest_zrk81.txt"
BATCH = 50


def md5(p, bs=1 << 20):
    h = hashlib.md5()
    with open(p, "rb") as f:
        while True:
            b = f.read(bs)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


files = []
for dp, _dn, fn in os.walk(SRC):
    for n in fn:
        fp = os.path.join(dp, n)
        files.append((os.path.relpath(fp, SRC).replace("\\", "/"), fp))
print("源文件数 =", len(files))

bad = []
for rel, fp in files:
    dp = os.path.join(DST, rel.replace("/", os.sep))
    if rel in WL:
        assert os.path.exists(SNAP), "白名单快照缺失: %s" % SNAP
        assert md5(SNAP) == WL[rel], "白名单快照 md5 不符"
        assert md5(fp) == WL[rel], "源件 md5 与白名单不符"
        print("  [白名单] %s :: 源件 md5 %s（快照已在 %s）" % (rel, WL[rel], SNAP))
        continue
    if not os.path.exists(dp):
        bad.append("MISSING " + rel); continue
    if os.path.getsize(fp) != os.path.getsize(dp):
        bad.append("SIZE " + rel); continue
    if md5(fp) != md5(dp):
        bad.append("MD5 " + rel); continue

if bad:
    print("FAIL-CLOSED:", bad[:10]); raise SystemExit(2)
print("校验 PASS（源 165 个文件全部在 waves/ 有逐字节对应，_gh.py 有快照）")

deleted = 0
with open(LOG, "a", encoding="utf-8", newline="\n") as log:
    log.write("# finish _z_rk81 %s\n" % time.strftime("%Y-%m-%d %H:%M:%S"))
    batch = []
    for rel, fp in files:
        batch.append((rel, fp))
        if len(batch) >= BATCH:
            for r, f in batch:
                os.remove(f); log.write("DEL\t%s\n" % f)
            deleted += len(batch); batch = []
            time.sleep(0.2)
            print("  deleted %d ..." % deleted, flush=True)
    for r, f in batch:
        os.remove(f); log.write("DEL\t%s\n" % f)
    deleted += len(batch)
print("deleted =", deleted)
left = sum(len(fn) for _r, _dd, fn in os.walk(SRC)) if os.path.exists(SRC) else -1
print("剩余文件 =", left)
dirs = sum(len(dd) for _r, dd, _f in os.walk(SRC)) if os.path.exists(SRC) else 0
print("剩余目录 =", dirs)
