# 本机 D 盘那份的两个小件：mmproj(907MB) + 分片1(11MB) 全量 sha256，对撞已知值
import hashlib, os, time

D = r"D:/Qwen3.8-Flash-Next-UD-IQ4_XS"
OUT = r"D:/workbuddy_space/strata_ws/deploy/tmp/_w714_dshard_small.txt"
KNOWN = {
    "mmproj-Qwen3.8-Flash-Next-BF16.gguf": {
        "huihui(mmproj, 唯一候选)": "b1a82259702816a5330d7bd7607cd9676b11780e79ff7348c21103ff3ce49bd0",
    },
    "Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf": {
        "两仓相同(meta/tokenizer)": "5ce89370720f8bf90890f439361282104c1aa1482d4013bb9a50923e758e71a4",
    },
}
lines = []
for f, c in KNOWN.items():
    p = os.path.join(D, f)
    t0 = time.time()
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        while True:
            b = fh.read(1 << 22)
            if not b:
                break
            h.update(b)
    x = h.hexdigest()
    dt = max(time.time() - t0, 1e-9)
    hit = [k for k, v in c.items() if x == v]
    lines.append("%s\n  size=%d\n  sha256=%s\n  elapsed=%.1fs\n  => %s\n"
                 % (f, os.path.getsize(p), x, dt,
                    ("**等于 " + hit[0] + "**") if hit else "**不匹配（异常，需并列完整值）**"))
    lines.append("  期望值 = %s\n\n" % list(c.values())[0])
open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
print("\n".join(lines))
