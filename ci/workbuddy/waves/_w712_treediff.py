# 全树对比：0.1.40.2 zip vs 0.1.40.4 zip（pristine，逐文件 md5）
import zipfile, os, hashlib, io

TR = r"D:/workbuddy_space/strata_ws/deploy/transfer"
OUT = r"D:/workbuddy_space/strata_ws/deploy/tmp/_w712_tree_diff.txt"

def idx(zp, tag):
    d = {}
    with zipfile.ZipFile(os.path.join(TR, zp)) as z:
        for n in z.namelist():
            if n.endswith("/"):
                continue
            rel = n.split("/", 1)[1] if "/" in n else n
            with z.open(n) as f:
                d[rel] = hashlib.md5(f.read()).hexdigest()
    return d

a = idx("strata-src-0.1.40.2.zip", "0.1.40.2")
b = idx("strata-src-0.1.40.4.zip", "0.1.40.4")
print("files:", len(a), len(b))

only_a = sorted(set(a) - set(b))
only_b = sorted(set(b) - set(a))
changed = sorted(k for k in set(a) & set(b) if a[k] != b[k])

lines = []
lines.append("== files only in 0.1.40.2 (%d) ==" % len(only_a))
lines += ["  " + x for x in only_a]
lines.append("== files only in 0.1.40.4 (%d) ==" % len(only_b))
lines += ["  " + x for x in only_b]
lines.append("== changed (%d) ==" % len(changed))
lines += ["  " + x for x in changed]

txt = "\n".join(lines)
open(OUT, "w", encoding="utf-8").write(txt)
print(txt[:6000])
print("...")
print("wrote", OUT)
