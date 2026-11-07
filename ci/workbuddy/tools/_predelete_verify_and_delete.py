# -*- coding: utf-8 -*-
"""删除前置校验 + 分批删除（fail-closed，含"预期差异"白名单与原件快照）。

铁律：
  1) 逐文件重算 源/新工作区 两侧的 (字节数, md5)；
  2) **源侧每个文件都必须在目标侧存在且完全一致** - 只有白名单里的相对路径允许"目标侧已更新"；
  3) 白名单里的每一个，删除前**先把源件快照进 tools/snapshots_premigrate/**，并断言快照 md5 等于源件 md5；
  4) 出现任何**白名单之外**的差异 => 立即中止，一个文件都不删（exit 2）；
  5) 通过后按每批 50 个文件删除，逐文件记 manifest。

判据与迁移期的差别（**故意放宽，写明**）：
  迁移期要求"文件集完全一致"；本次只要求 **源 ⊆ 目标**（迁移后新工作区有新增文件，属正常）。

用法：
  python tools/_predelete_verify_and_delete.py          # 只校验
  python tools/_predelete_verify_and_delete.py --go      # 校验通过后真删
"""
import hashlib
import os
import shutil
import sys
import time

PAIRS = [
    (r"D:\strata166", r"D:\workbuddy_space\strata_ws\deploy"),
    (r"D:\workbuddy\_z_rk81", r"D:\workbuddy_space\strata_ws\waves"),
]
TOOLS = r"D:\workbuddy_space\strata_ws\tools"
SNAP = os.path.join(TOOLS, "snapshots_premigrate")
BATCH = 50
GO = "--go" in sys.argv

# 白名单：源件与新工作区件**允许不同**的路径（目标侧是"有意更新过"的版本）。
# 每个都必须有书面依据，且删除前会快照源件。
EXPECTED_DIFF = {
    r"D:\strata166": {
        "configs/workbuddy-strata166.md":
            "本波(W712)按 0.1.40.4 升级更新了头部/§6/§9，并清了存量禁用码位；"
            "源件为 0.1.40.2 时代的 7324 B 版本，删除前快照留档",
    },
    r"D:\workbuddy\_z_rk81": {
        "_gh.py":
            "迁移时**有意**改一处：TOKF 由旧 _z_rk81 路径改指新工作区（+14 B），"
            "见 MAP_OLD_TO_NEW.md；源件为改前的 3042 B 版本，删除前快照留档",
    },
}

REPORT = os.path.join(TOOLS, "_predelete_report.md")
DLOG = os.path.join(TOOLS, "_delete_manifest_%s.txt" % time.strftime("%Y%m%d_%H%M%S"))


def md5_of(p, bs=1 << 20):
    h = hashlib.md5()
    with open(p, "rb") as f:
        while True:
            b = f.read(bs)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def walk_files(root):
    out = []
    for dp, _dn, fn in os.walk(root):
        for n in fn:
            fp = os.path.join(dp, n)
            out.append((os.path.relpath(fp, root).replace("\\", "/"), fp))
    return out


def snap(src, dst_root, rel, tag):
    """把源件快照到 tools/snapshots_premigrate/<tag>/<rel>，断言 md5 相等。"""
    out = os.path.join(SNAP, tag, rel.replace("/", os.sep))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    shutil.copy2(src, out)
    a, b = md5_of(src), md5_of(out)
    assert a == b, "SNAPSHOT_MD5_MISMATCH %s %s != %s" % (rel, a, b)
    return out, a, os.path.getsize(src)


def main():
    rl = ["# 删除前置校验报告  %s" % time.strftime("%Y-%m-%d %H:%M:%S"), ""]
    plan, hard_fail, snaps = [], False, []

    for src, dst in PAIRS:
        if not os.path.isdir(src):
            rl.append("## %s -> %s" % (src, dst))
            rl.append("- 源目录不存在（可能已删）：跳过")
            rl.append("")
            continue
        wl = EXPECTED_DIFF.get(src, {})
        files = walk_files(src)
        miss, sbad, mbad, ok = [], [], [], 0
        nbytes = 0
        for rel, fp in files:
            dp = os.path.join(dst, rel.replace("/", os.sep))
            try:
                sa = os.path.getsize(fp)
            except OSError as e:
                sbad.append("%s (%r)" % (rel, e))
                continue
            if not os.path.exists(dp):
                miss.append(rel)
                continue
            if sa != os.path.getsize(dp):
                if rel in wl:
                    out, m, n = snap(fp, SNAP, rel, os.path.basename(src))
                    snaps.append((rel, out, m, n))
                    continue
                sbad.append("%s %d != %d" % (rel, sa, os.path.getsize(dp)))
                continue
            if md5_of(fp) != md5_of(dp):
                if rel in wl:
                    out, m, n = snap(fp, SNAP, rel, os.path.basename(src))
                    snaps.append((rel, out, m, n))
                    continue
                mbad.append(rel)
                continue
            ok += 1
            nbytes += sa
        pass_ = not (miss or sbad or mbad)
        rl.append("## %s -> %s" % (src, dst))
        rl.append("- 源文件数=%d  源字节=%d" % (len(files), sum(
            os.path.getsize(fp) for _r, fp in files if os.path.exists(fp))))
        rl.append("- 逐字节相同=%d  目标侧缺失=%d  字节数不符=%d  md5不符=%d  白名单内差异=%d"
                  % (ok, len(miss), len(sbad), len(mbad), len(wl)))
        for x in miss[:10]:
            rl.append("    [缺失] " + x)
        for x in sbad[:10]:
            rl.append("    [字节] " + x)
        for x in mbad[:10]:
            rl.append("    [md5 ] " + x)
        for rel, note in wl.items():
            rl.append("    [白名单] %s :: %s" % (rel, note))
        rl.append("- 判定: **%s**" % ("PASS" if pass_ else "FAIL"))
        rl.append("")
        if not pass_:
            hard_fail = True
        else:
            plan.append((src, files))

    if snaps:
        rl.append("## 原件快照（删除前留档）")
        for rel, out, m, n in snaps:
            rl.append("- %s  ->  %s  (%d B, md5 %s)" % (rel, out, n, m))
        rl.append("")

    rl.append("## 总判定")
    rl.append("- **%s**" % ("ALL PASS -> 可删" if not hard_fail else "FAIL -> 禁止删除"))
    rl.append("- 待删文件合计=%d" % sum(len(f) for _s, f in plan))
    rl.append("- 模式: %s" % ("DELETE（--go）" if GO else "DRY-RUN（仅校验）"))
    txt = "\n".join(rl) + "\n"
    with open(REPORT, "w", encoding="utf-8", newline="\n") as f:
        f.write(txt)
    print(txt)
    print("report:", REPORT)

    if hard_fail:
        print("FAIL-CLOSED: 校验未过，不删任何文件")
        return 2
    if not GO:
        print("DRY-RUN 完成；加 --go 才真删")
        return 0

    deleted = 0
    with open(DLOG, "a", encoding="utf-8", newline="\n") as log:
        log.write("# delete manifest %s  (batch=%d)\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), BATCH))
        for src, files in plan:
            batch = []
            for rel, fp in files:
                batch.append((rel, fp))
                if len(batch) >= BATCH:
                    _flush(batch, log)
                    deleted += len(batch)
                    batch = []
                    time.sleep(0.2)
                    print("  deleted %d ..." % deleted, flush=True)
            if batch:
                _flush(batch, log)
                deleted += len(batch)
            for dp, _dn, _fn in os.walk(src, topdown=False):
                try:
                    os.rmdir(dp)
                except OSError:
                    pass
        left = [s for s, _f in plan if os.path.exists(s)]
        log.write("# deleted=%d  remaining=%s\n" % (deleted, left))
    print("deleted=%d" % deleted)
    print("remaining source dirs:", left if left else "(none)")
    return 0 if not left else 3


def _flush(batch, log):
    for rel, fp in batch:
        try:
            os.remove(fp)
            log.write("DEL\t%s\n" % fp)
        except OSError as e:
            log.write("ERR\t%s\t%r\n" % (fp, e))
            raise SystemExit("FAIL-CLOSED: 删除 %s 失败：%r" % (fp, e))


if __name__ == "__main__":
    sys.exit(main())
