import io, os, re, shutil

WT = "/home/albus/strata166/pr/k10"

# (a) #30168 added prec_src1 to ggml_cuda_mmq_get_config(host): (type, J, fallback, cc, ggml_prec)
p = os.path.join(WT, "src/prefill/moe_mmq.cu")
s = io.open(p, encoding="utf-8").read()
shutil.copy2(p, p + ".bak_k10b")
out, n = [], 0
for ln in s.split("\n"):
    if "ggml_cuda_mmq_get_config(" in ln and "GGML_PREC_Q8" not in ln:
        t = ln.replace(", info.devices[id].cc);", ", info.devices[id].cc, GGML_PREC_Q8);")
        if t == ln:
            t = ln.replace(", cc);", ", cc, GGML_PREC_Q8);")
        if t != ln:
            n += 1
        out.append(t)
    else:
        out.append(ln)
io.open(p, "w", encoding="utf-8", newline="\n").write("\n".join(out))
print("moe_mmq.cu: get_config call sites patched =", n)

# (b) b12110's ggml_backend_cuda_context::new_pool_for_device gained a ctx parameter
p2 = os.path.join(WT, "src/prefill/ggml_cuda_host.cu")
s2 = io.open(p2, encoding="utf-8").read()
OLD = "ggml_backend_cuda_context::new_pool_for_device(int, int) {"
NEW = "ggml_backend_cuda_context::new_pool_for_device(ggml_backend_cuda_context &, int, int) {"
if NEW in s2:
    print("ggml_cuda_host.cu: already patched")
elif OLD in s2:
    shutil.copy2(p2, p2 + ".bak_k10b")
    io.open(p2, "w", encoding="utf-8", newline="\n").write(s2.replace(OLD, NEW, 1))
    print("ggml_cuda_host.cu: new_pool_for_device patched")
else:
    print("WARN ggml_cuda_host.cu: anchor missing")

# 还有没有别的 1-元 ggml_cuda_mmq_get_config 调用？
rc = os.system("grep -rn 'ggml_cuda_mmq_get_config(' %s/src | grep -v GGML_PREC_Q8 | grep -v 'mmq.cuh'" % WT)
print("remaining (rc=%d, 0 = none)" % rc)
