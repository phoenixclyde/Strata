import io, os, shutil, subprocess, sys

R = "/home/albus/strata166/tmp/w1037"
WT = "/home/albus/strata166/pr/k10"
FORK = "/home/albus/strata166/pr/strata-fork"


def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


if not os.path.isdir(WT):
    rc, out = sh("git -C %s worktree add --detach %s gfx906/mi50" % (FORK, WT))
    print("worktree:", rc, out.strip().splitlines()[-1] if out.strip() else "")

P = os.path.join(WT, "src/prefill/mmq_nvfp4_w4a4.cu")
s = io.open(P, encoding="utf-8").read()
OLD = "strata_w4a4_mul_mat_q_case<GGML_TYPE_NVFP4>(ctx, a, s)"
NEW = "strata_w4a4_mul_mat_q_case<GGML_TYPE_NVFP4, GGML_PREC_Q8>(ctx, a, s)"
if NEW in s:
    print("already patched")
elif OLD in s:
    shutil.copy2(P, P + ".bak_k10")
    t = s.replace(OLD, NEW, 1)
    assert NEW in t
    io.open(P, "w", encoding="utf-8", newline="\n").write(t)
    print("patched", P)
else:
    print("FAIL: anchor not found")
    sys.exit(2)

# what else mentions the two-arg form in our tree?  (the other API deltas R100 counted)
rc, out = sh("grep -rn 'mul_mat_q_case<' %s/src --include=*.cu --include=*.cuh | head -10" % WT)
print(out.strip())
