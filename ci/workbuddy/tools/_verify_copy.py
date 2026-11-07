# -*- coding: utf-8 -*-
"""迁入校验器：逐文件比对 源 与 新工作区 的 (字节数, md5)，并落一份清单。

判据（缺一即 FAIL）：
  1) 文件集完全一致（无缺失、无多余）
  2) 每个文件的字节数一致
  3) 每个文件的 md5 一致
只有三项全 PASS 才允许进入删除阶段。
"""
import hashlib
import html
import os
import sys
import time

PAIRS = [
    (r"D:\strata166", r"D:\workbuddy_space\strata_ws\deploy"),
    (r"D:\workbuddy\_z_rk81", r"D:\workbuddy_space\strata_ws\waves"),
]
# 迁入后「有意修改」的文件（相对路径）。这些不计入 FAIL，但要单独报出来。
EXPECTED_DIFF = {
    r"D:\workbuddy_space\strata_ws\waves": {
        "_gh.py",  # TOKF 由旧 _z_rk81 路径改指新工作区（+14 B）
    },
}
OUTDIR = r"D:\workbuddy_space\strata_ws\tools"


def md5_of(path, bs=1 << 20):
    h = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            b = f.read(bs)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def manifest(root):
    m = {}
    for dp, _dn, fn in os.walk(root):
        for name in fn:
            fp = os.path.join(dp, name)
            rel = os.path.relpath(fp, root).replace("\\", "/")
            try:
                st = os.stat(fp)
                m[rel] = (st.st_size, md5_of(fp))
            except OSError as e:
                m[rel] = (-1, "ERR:%s" % e)
    return m


def main():
    lines = []
    lines.append("# 迁入校验报告  %s" % time.strftime("%Y-%m-%d %H:%M:%S"))
    lines.append("")
    overall_ok = True
    for src, dst in PAIRS:
        lines.append("## %s  ->  %s" % (src, dst))
        a = manifest(src)
        b = manifest(dst)
        ka, kb = set(a), set(b)
        only_src = sorted(ka - kb)
        only_dst = sorted(kb - ka)
        common = ka & kb
        exp = EXPECTED_DIFF.get(dst, set())
        size_bad, md5_bad, exp_hit = [], [], []
        for k in sorted(common):
            if a[k][0] != b[k][0]:
                if k in exp:
                    exp_hit.append((k, a[k][0], b[k][0]))
                else:
                    size_bad.append(k)
            elif a[k][1] != b[k][1]:
                if k in exp:
                    exp_hit.append((k, a[k][1], b[k][1]))
                else:
                    md5_bad.append(k)
        n = len(common)
        bytes_a = sum(v[0] for v in a.values() if v[0] >= 0)
        bytes_b = sum(v[0] for v in b.values() if v[0] >= 0)
        ok = (not only_src) and (not only_dst) and (not size_bad) and (not md5_bad)
        overall_ok = overall_ok and ok
        lines.append("- 源文件数=%d  目标文件数=%d  共有=%d" % (len(a), len(b), n))
        lines.append("- 源字节=%d  目标字节=%d  差=%d" % (bytes_a, bytes_b, bytes_b - bytes_a))
        lines.append("- 仅源有=%d  仅目标有=%d  字节数不符=%d  md5不符=%d  预期内差异=%d"
                     % (len(only_src), len(only_dst), len(size_bad), len(md5_bad), len(exp_hit)))
        for k, x, y in exp_hit:
            lines.append("    [预期内] %s  %s -> %s（有意改动，见 MAP_OLD_TO_NEW.md 第二节）" % (k, x, y))
        for k in only_src[:20]:
            lines.append("    [仅源] " + k)
        for k in only_dst[:20]:
            lines.append("    [仅目标] " + k)
        for k in size_bad[:20]:
            lines.append("    [字节] %s  %d != %d" % (k, a[k][0], b[k][0]))
        for k in md5_bad[:20]:
            lines.append("    [md5 ] %s  %s != %s" % (k, a[k][1], b[k][1]))
        lines.append("- 判定: **%s**" % ("PASS" if ok else "FAIL"))
        lines.append("")
    lines.append("## 总判定")
    lines.append("- **%s**" % ("ALL PASS" if overall_ok else "FAIL（禁止删除原件）"))
    txt = "\n".join(lines) + "\n"
    os.makedirs(OUTDIR, exist_ok=True)
    p = os.path.join(OUTDIR, "_verify_copy_out.md")
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(txt)
    print(txt)
    return 0 if overall_ok else 2


if __name__ == "__main__":
    sys.exit(main())
