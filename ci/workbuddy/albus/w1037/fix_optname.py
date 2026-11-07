import io
P = "/home/albus/strata166/pr/port-all/src/kernels/cuda/qsa_decode_attn.cu"
s = io.open(P, encoding="utf-8").read()
a = "const int opt_chunk = gfx906_attn_opt();"
b = "const int opt = gfx906_attn_opt();"
if a in s:
    s = s.replace(a, b, 1).replace("opt_chunk != 0", "opt != 0", 1)
    io.open(P, "w", encoding="utf-8", newline="\n").write(s)
    print("renamed")
elif b in s:
    print("already named opt")
else:
    print("WARN anchor missing")
