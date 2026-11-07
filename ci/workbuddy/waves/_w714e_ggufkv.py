# 正规 GGUF KV 解析：读出 general.name / basename / finetune / license 等值（判定发布者）
import io, os, struct, glob

D = r"D:/Qwen3.8-Flash-Next-UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf"
f = open(D, "rb")
magic = f.read(4)
ver = struct.unpack("<I", f.read(4))[0]
nt = struct.unpack("<Q", f.read(8))[0]
nk = struct.unpack("<Q", f.read(8))[0]
print("magic=%s version=%d tensors=%d kv_pairs=%d" % (magic, ver, nt, nk))

SZ = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 7: 1, 10: 8, 11: 8, 12: 8}


def rd_str():
    n = struct.unpack("<Q", f.read(8))[0]
    return f.read(n).decode("utf-8", "replace")


def rd_val(t):
    if t == 8:
        return rd_str()
    if t == 9:
        et = struct.unpack("<I", f.read(4))[0]
        cnt = struct.unpack("<Q", f.read(8))[0]
        if et == 8:
            return "[%d strings] " % cnt + "; ".join(rd_str() for _ in range(min(cnt, 8)))
        f.read(SZ.get(et, 1) * cnt)
        return "[array of %d type %d]" % (cnt, et)
    if t == 7:
        return bool(struct.unpack("<?", f.read(1))[0])
    fmt = {0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i", 6: "<f", 10: "<Q", 11: "<q", 12: "<d"}.get(t)
    return struct.unpack(fmt, f.read(SZ[t]))[0] if fmt else "?"

print("=== KV 对（只详细打印非张量类的关键项）===")
for i in range(nk):
    k = rd_str()
    t = struct.unpack("<I", f.read(4))[0]
    v = rd_val(t)
    ks = str(k)
    if not ks.startswith("tokenizer.ggml.") or ks in ("tokenizer.ggml.model",):
        sv = str(v)
        print("  %-34s (t=%d) %s" % (ks, t, sv[:200]))
f.close()

print()
print("=== 我们工作区当初的下载/推送日志 ===")
WS = r"D:/workbuddy_space/strata_ws"
for p in sorted(glob.glob(os.path.join(WS, "deploy/logs/_*iq4xs*.txt")) + glob.glob(os.path.join(WS, "deploy/logs/_push_weights.txt"))):
    print("---- %s (%d B)" % (os.path.relpath(p, WS), os.path.getsize(p)))
    t = io.open(p, encoding="utf-8", errors="replace").read()
    for ln in t.splitlines()[:28]:
        print("     ", ln[:190])
