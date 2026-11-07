# 后台：本机 D 盘那份（机主说"已下载完"的目录）分片 2/3 全量 sha256，对撞两个候选
import hashlib, os, time

D = r"D:/Qwen3.8-Flash-Next-UD-IQ4_XS"
OUT = r"D:/workbuddy_space/strata_ws/deploy/tmp/_w714_dshard_hash.txt"
CAND = {
    "Qwen3.8-Flash-Next-UD-IQ4_XS-00002-of-00003.gguf": {
        "base(官方 Unsloth)": "577a38a2392b40ca2193cea502e1d92f60b8cd370675d308e0ec21885d9daaa7",
        "huihui(abliterated)": "c67b468b3b83bc12",
    },
    "Qwen3.8-Flash-Next-UD-IQ4_XS-00003-of-00003.gguf": {
        "base(官方 Unsloth)": "d4634e6d84f0ebb0940be15c90d3790bf6464e3dea3a1cddc567dc0e83ad8833",
        "huihui(abliterated)": "130560b6a447e0fe",
    },
}
lines = []
for f, c in CAND.items():
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
    dt = time.time() - t0
    verdict = [k for k, v in c.items() if x == v or x.startswith(v)]
    lines.append("%s\n  size=%d\n  sha256=%s\n  elapsed=%.0fs (%.0f MB/s)\n  => %s\n"
                 % (f, os.path.getsize(p), x, dt, os.path.getsize(p) / dt / 1e6,
                    ("**等于 " + verdict[0] + "**") if verdict else "两个候选都不匹配（需并列完整值）"))
    lines.append("  候选 base  = %s\n" % c["base(官方 Unsloth)"])
    lines.append("  候选 huihui= %s\n\n" % c["huihui(abliterated)"])
open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
print("\n".join(lines))
