# 决定性对比：两个 D: 副本（IDM 旧件 vs 新下的 huihui 件）逐片抽样哈希 + 两份的 GGUF 元数据
import hashlib, os, struct, io

A = r"D:/IDM/Strata-UDIQ4XS"                                   # 当初推 166 的那份
B = r"D:/Qwen3.8-Flash-Next-UD-IQ4_XS"                          # 机主说刚从 huihui-ai/...-abliterated-GGUF 下的
SH = ["Qwen3.8-Flash-Next-UD-IQ4_XS-0000%d-of-00003.gguf" % i for i in (1, 2, 3)]


def sample(path):
    sz = os.path.getsize(path)
    out = []
    with open(path, "rb") as f:
        for off in (0, sz // 2, max(0, sz - 32 * 1024 * 1024)):
            f.seek(off)
            out.append(hashlib.md5(f.read(32 * 1024 * 1024)).hexdigest())
    return sz, out


print("=== 逐片对比（size + 首/中/尾 各 32 MB 的 md5）===")
for name in SH:
    pa, pb = os.path.join(A, name), os.path.join(B, name)
    if not (os.path.exists(pa) and os.path.exists(pb)):
        print("  %-52s 一侧缺（A=%s B=%s）" % (name, os.path.exists(pa), os.path.exists(pb))); continue
    sa, ha = sample(pa)
    sb, hb = sample(pb)
    same = (sa == sb) and (ha == hb)
    print("  %-52s %s  size %d / %d  head %s mid %s tail %s"
          % (name, "**相同**" if same else "**不同**", sa, sb,
             "same" if ha[0] == hb[0] else "DIFF", "same" if ha[1] == hb[1] else "DIFF",
             "same" if ha[2] == hb[2] else "DIFF"))
    if not same:
        print("      A: %s" % ha)
        print("      B: %s" % hb)


def kv(path):
    f = open(path, "rb")
    f.read(4); struct.unpack("<I", f.read(4))[0]
    nt = struct.unpack("<Q", f.read(8))[0]; nk = struct.unpack("<Q", f.read(8))[0]
    SZ = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 7: 1, 10: 8, 11: 8, 12: 8}

    def rs():
        n = struct.unpack("<Q", f.read(8))[0]
        return f.read(n).decode("utf-8", "replace")

    def rv(t):
        if t == 8:
            return rs()
        if t == 9:
            et = struct.unpack("<I", f.read(4))[0]; c = struct.unpack("<Q", f.read(8))[0]
            if et == 8:
                return "[%d strings] %s" % (c, "; ".join(rs() for _ in range(min(c, 6))))
            f.read(SZ.get(et, 1) * c)
            return "[array %d]" % c
        if t == 7:
            return bool(struct.unpack("<?", f.read(1))[0])
        fmt = {0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i", 6: "<f", 10: "<Q", 11: "<q", 12: "<d"}.get(t)
        return struct.unpack(fmt, f.read(SZ[t]))[0] if fmt else "?"

    d = {}
    for _ in range(nk):
        try:
            k = rs(); t = struct.unpack("<I", f.read(4))[0]; d[str(k)] = str(rv(t))
        except Exception:
            break
    f.close()
    return nt, d


print()
print("=== 两片 1 的 GGUF 元数据关键项 ===")
for lab, root in (("IDM 旧件", A), ("新下(huihui)", B)):
    p = os.path.join(root, SH[0])
    if not os.path.exists(p):
        print("  %s 不存在" % lab); continue
    nt, d = kv(p)
    print("  --- %s (tensors=%d, kv=%d)" % (lab, nt, len(d)))
    for k in sorted(d):
        if k.startswith(("general.", "license")) or "name" in k or "finetune" in k or "quant" in k:
            print("      %-36s %s" % (k, d[k][:120]))
