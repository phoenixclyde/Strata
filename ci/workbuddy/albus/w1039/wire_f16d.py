import io

P = "/home/albus/strata166/pr/port-all/src/kernels/cuda/qsa_decode_attn.cu"
s = io.open(P, encoding="utf-8").read()

OLD = """        const char* c = std::getenv("STRATA_GFX906_ATTN_LDS_PAD");
        if (a && a[0] == '1') o |= 1;
        if (b && b[0] == '1') o |= 2;
        if (c && c[0] == '1') o |= 4;
        return o;"""

NEW = """        const char* c = std::getenv("STRATA_GFX906_ATTN_LDS_PAD");
        const char* d = std::getenv("STRATA_GFX906_ATTN_F16D");   // W1039: bit 3, fp16 query + v_dot2_f32_f16
        if (a && a[0] == '1') o |= 1;
        if (b && b[0] == '1') o |= 2;
        if (c && c[0] == '1') o |= 4;
        if (d && d[0] == '1') o |= 8;
        return o;"""

assert OLD in s, "anchor missing"
io.open(P, "w", encoding="utf-8", newline="\n").write(s.replace(OLD, NEW, 1))
print("ATTN_F16D wired to bit 3")
