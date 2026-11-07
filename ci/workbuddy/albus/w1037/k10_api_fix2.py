import io, os, re, shutil, subprocess, sys

WT = "/home/albus/strata166/pr/k10"
SRC = os.path.join(WT, "src")

# Upstream moved mul_mat_q_case from 1 template parameter to 2: <type, GGML_PREC_Q8>.
# Our tree is written against the 1-parameter form (pin b11062), so every call site needs the precision arg.
pat = re.compile(r"(mul_mat_q_case<GGML_TYPE_[A-Z0-9_]+)(>\(\s*ctx)")
total = 0
for root, _, files in os.walk(SRC):
    for fn in files:
        if not fn.endswith((".cu", ".cuh")):
            continue
        p = os.path.join(root, fn)
        s = io.open(p, encoding="utf-8", errors="replace").read()
        t, n = pat.subn(r"\1, GGML_PREC_Q8\2", s)
        if n:
            shutil.copy2(p, p + ".bak_k10")
            io.open(p, "w", encoding="utf-8", newline="\n").write(t)
            total += n
            print("%-46s %d" % (os.path.relpath(p, WT), n))
print("call sites patched:", total)

rc = subprocess.run(["bash", "-lc", "grep -rn 'mul_mat_q_case<GGML_TYPE_[A-Z0-9_]*>(' %s --include=*.cu --include=*.cuh | wc -l" % SRC],
                    capture_output=True, text=True)
print("remaining 1-arg call sites:", rc.stdout.strip())
