# 本机基准：对候选目录逐片取 head/mid/tail（各16MB）md5，作为与 166 现场对撞的参照
import hashlib, os

CANDS = {
    "D盘(机主下, 已证=huihui)": r"D:/Qwen3.8-Flash-Next-UD-IQ4_XS",
    "IDM(当初推166那份)": r"D:/IDM/Strata-UDIQ4XS",
}
SH = ["Qwen3.8-Flash-Next-UD-IQ4_XS-0000%d-of-00003.gguf" % i for i in (1, 2, 3)]


def slab(path, off, n=16 << 20):
    with open(path, "rb") as f:
        f.seek(off)
        return hashlib.md5(f.read(n)).hexdigest()


for lab, root in CANDS.items():
    print("== %s  (%s)" % (lab, root))
    if not os.path.isdir(root):
        print("   (目录不存在)"); continue
    for name in SH:
        p = os.path.join(root, name)
        if not os.path.exists(p):
            print("   %-52s (缺)" % name); continue
        sz = os.path.getsize(p)
        mid = (sz // 2) // (1 << 20) * (1 << 20)
        print("   %-52s size=%d" % (name, sz))
        print("       head=%s" % slab(p, 0))
        print("       mid =%s" % slab(p, mid))
        print("       tail=%s" % slab(p, max(0, sz - (16 << 20))))
    mm = os.path.join(root, "mmproj-Qwen3.8-Flash-Next-BF16.gguf")
    if os.path.exists(mm):
        h = hashlib.sha256(open(mm, "rb").read()).hexdigest()
        print("   mmproj sha256=%s" % h)
    print()
