import subprocess, base64
def sh(s, t=900):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
docker run --rm --entrypoint bash strata-gfx906:0.2.4p4 -c '
set -e
/opt/rocm/llvm/bin/llvm-objcopy --dump-section .hip_fatbin=/tmp/fat.bin /src/build-906/strata
/opt/rocm/llvm/bin/clang-offload-bundler -unbundle -type=o -targets=hipv4-amdgcn-amd-amdhsa--gfx906 -inputs=/tmp/fat.bin -outputs=/tmp/gfx906.o 2>&1 | tail -2
/opt/rocm/llvm/bin/llvm-readobj --notes /tmp/gfx906.o > /tmp/notes.txt 2>/dev/null
wc -l /tmp/notes.txt
python3 - <<PY
import re
txt = open("/tmp/notes.txt", errors="replace").read()
recs = txt.split("- .args:")
rows = []
for r in recs:
    if "mul_mat_q" not in r: continue
    def g(k):
        m = re.search(r"^\s*\.%s:/s*(/S+)" % k, r, re.M)
        return m.group(1) if m else "?"
    name = g("name")
    rows.append((name, int(g("group_segment_fixed_size")), int(g("vgpr_count")), int(g("vgpr_spill_count")),
                 int(g("private_segment_fixed_size")), int(g("max_flat_workgroup_size")), int(g("sgpr_spill_count"))))
print("mul_mat_q kernels:", len(rows))
def key(n):
    m = re.search(r"mul_mat_qIL9ggml_type(\d+)ELi(\d+)ELb(\d)", n)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else (999,0,0)
rows.sort(key=lambda x: key(x[0]))
print("%-62s %7s %5s %4s %6s %5s %4s" % ("kernel(suffix)", "LDS", "VGPR", "vsp", "psize", "wgsz", "ssp"))
for name, lds, vgpr, vsp, psz, wgsz, ssp in rows:
    if int(re.search(r"ELi(\d+)ELb(\d)", name).group(2)) not in (0,):
        pass
    typ, J, fb = key(name)
    print("%-10s J=%-3d fb=%d %-6s %7d %5d %4d %6d %5d %4d" % ("IQ/t%d"%typ, J, fb, "", lds, vgpr, vsp, psz, wgsz, ssp))
PY
' 2>&1 | tail -60
''', t=900))
