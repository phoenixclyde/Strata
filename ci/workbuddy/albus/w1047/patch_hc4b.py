import pathlib
import subprocess

R = pathlib.Path("/home/albus/strata166/pr/k10")
F = R / "src/kernels/cuda/fused_gr.cu"
BR = "gfx906/hc-dp4a"


def git(*args):
    return subprocess.run(["git", "-C", str(R)] + list(args), check=True, text=True,
                          stdout=subprocess.PIPE).stdout.strip()

if git("status", "--porcelain"):
    raise SystemExit("tree dirty")
git("checkout", BR)
s = F.read_text(encoding="utf-8")
old = "    if (dp4a) gr_down_q8_dp4a_kernel<T><<<dim3(Q8_RG + 1, Q8_NKC), THREADS, 0, st>>>(m, part, ssg);"
new = ("    // W1047: the clean bench showed the activation-quantized kernel wins at T<=6\n"
       "    // but loses badly at T=7/8 (shared-memory/occupancy cliff). Default safe cutoff.\n"
       "    static const int dp4a_max_t = [] {\n"
       "        const char* v = std::getenv(\"STRATA_HC_DOWN_DP4A_MAX_T\");\n"
       "        return v != nullptr ? std::atoi(v) : 6;\n"
       "    }();\n"
       "    if (dp4a && T <= dp4a_max_t) gr_down_q8_dp4a_kernel<T><<<dim3(Q8_RG + 1, Q8_NKC), THREADS, 0, st>>>(m, part, ssg);")
assert s.count(old) == 1
s = s.replace(old, new, 1)
F.write_text(s, encoding="utf-8", newline="\n")
git("add", "src/kernels/cuda/fused_gr.cu")
git("commit", "-m", "gfx906: gate HC down DP4A to T<=6 after clean bench cliff")
print("commit", git("rev-parse", "--short", "HEAD"))
print(git("show", "--stat", "--oneline", "HEAD"))
