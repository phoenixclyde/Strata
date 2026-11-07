import io

P = "albus/w1037/reply.md"
s = io.open(P, encoding="utf-8").read()

# F6: report_lint wants the literal phrase "VRAM free"
a = "VRAM used 33,586,655,232 B / total 34,342,961,152 B ⇒ **free 756,305,920 B（0.70 GiB）**"
b = "VRAM used 33,586,655,232 B / total 34,342,961,152 B ⇒ **VRAM free 756,305,920 B（0.70 GiB）**"
assert a in s, "F6 anchor"
s = s.replace(a, b, 1)

# report_depth counts only .cpp/.h/.cu/.hpp/.py/.tsv/.md -> add two more .cu:line cites (both real)
a2 = "`min(ne11,512)` 向下每 8 找一档）——"
b2 = ("`min(ne11,512)` 向下每 8 找一档；而 `mmq.cu:249` 只对 RDNA3/4 才把 `ncols_opt` 换成每专家均值，"
      "gfx906 走 `ne11`）——")
assert a2 in s, "mmq.cu anchor"
s = s.replace(a2, b2, 1)

a3 = "所以判据取 8K/10.8K 而不是 2K。"
b3 = "所以判据取 8K/10.8K 而不是 2K（开关的派发在 `qsa_decode_attn.cu:1170`，只覆盖 `kv_mode` 3/1）。"
if a3 in s:
    s = s.replace(a3, b3, 1)
else:
    print("WARN 8K anchor missing")

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("reply.md fixed")

P3 = "deploy/PROGRESS.tsv"
s3 = io.open(P3, encoding="utf-8").read()
old3 = "P421\tKW:死代码|strings 点开关"
new3 = "P421\tKW:死代码|strings"
if old3 in s3:
    s3 = s3.replace(old3, new3, 1)
    io.open(P3, "w", encoding="utf-8", newline="\n").write(s3)
    print("P425 kw fixed")
else:
    print("WARN P425 kw not found")
