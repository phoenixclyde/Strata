# 把 W712 B1 的边界结论写进 register 的 P34（只动 evidence/verdict，不动 value/status）
import hashlib, io, os, shutil, time, collections

REG = r"D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv"
raw = open(REG, "rb").read()
print("before md5", hashlib.md5(raw).hexdigest(), len(raw), "bytes")

bak = REG + ".bak_w712_" + time.strftime("%Y%m%d_%H%M%S")
shutil.copy2(REG, bak)
print("backup ->", os.path.basename(bak))

text = raw.decode("utf-8")
lines = text.splitlines(keepends=False)
hdr = lines[0].split("\t")
IE, IV = hdr.index("evidence"), hdr.index("verdict")

NEW_EV = (
    "W709 交错 A/B（~10,000-token prompt）：默认 16384 -> reused=0、温 TTFT 23.07/23.07s；"
    "8192 -> reused=8192、温 TTFT 5.86/5.88s = -74.6%；对照 4096 -> reused=0。"
    "机制：可复用前缀须与 prefill chunk(8192) 对齐。"
    "W712 B1 边界扫描（3 臂 x 3 档，单变量，Z0=off；档内 2 轮）："
    "<8k(约 4,589 tok) 三臂 reused 恒 0、温 TTFT 10.472/10.496/10.464s 约等于冷 10.83~10.88s（整条 prompt 不足一个 chunk，无 checkpoint 可放，该档换任何值都无用）；"
    "8-16k(约 9,989 tok) 8192 -> reused=8192、温 5.866s，而 16384/32768 -> reused=0、温 23.066/23.147s（约等于冷 23.10s，即 -74.6% 对 0）；"
    ">16k(约 23,939 tok) 8192/16384 -> reused=16384、温 16.990/16.989s，而 32768 -> reused=0、温 50.181s（约等于冷 49.99s）。"
    "=> 越大越好在 >16k 档不成立（checkpoint 落在 prompt 之外即全无用）。"
    "成本：checkpoint 计入 --prompt-cache N(=6) 上限（help：约 118 MB/个）=> 上限约 0.7 GB RAM（B1 未实测曲线）"
)
NEW_VD = (
    "采纳（边界已实测）：受益域 = 仅 8k~16k-token 会话（温 TTFT -74.6%）；"
    "<8k 无复用（chunk 机制所限，与该值无关，短会话每轮仍需整条重预填）；"
    ">16k 与 16384 等效，32768 反而归零 => 8192 是在三档上都不劣的唯一档位"
)

n = 0
out = []
for i, ln in enumerate(lines):
    if not ln.strip():
        out.append(ln); continue
    c = ln.split("\t")
    if c[0] == "P34":
        assert len(c) == len(hdr), "列数不符"
        assert c[hdr.index("status")] == "ADOPTED" and c[hdr.index("value")] == "8192", "P34 形态变了，先人工核"
        c[IE], c[IV] = NEW_EV, NEW_VD
        ln = "\t".join(c)
        n += 1
    out.append(ln)
assert n == 1, "P34 命中 %d 次（应为 1）" % n

io.open(REG, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")

raw2 = open(REG, "rb").read()
rows = [l for l in raw2.decode("utf-8").splitlines() if l.strip()]
st = collections.Counter(r.split("\t")[hdr.index("status")] for r in rows[1:])
BAN = [0x21D2, 0x2192, 0x2014, 0x2013, 0x2026, 0x2265, 0x2264, 0x2260, 0x2212, 0x00D7]
print("after  md5", hashlib.md5(raw2).hexdigest(), len(raw2), "bytes")
print("rows =", len(rows) - 1, " status =", dict(st))
print("CR =", raw2.count(b"\r"), " BAN =", sum(1 for ch in raw2.decode("utf-8") if ord(ch) in BAN))
print("tabs per row ok:", all(len(l.split("\t")) == len(hdr) for l in rows))
