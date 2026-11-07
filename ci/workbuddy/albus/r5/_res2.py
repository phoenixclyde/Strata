import subprocess, base64
def sh(s, t=1200):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
docker run --rm --entrypoint bash strata-gfx906:0.2.4p4 -c '
cd /src/build-906
python3 - <<PY
import subprocess, re, sys
cmds = subprocess.run(["ninja","-t","commands"], capture_output=True, text=True).stdout.splitlines()
c = [x for x in cmds if "mmq-instance-iq3_s.cu" in x and "clang" in x]
print("found", len(c))
cmd = c[0]
cmd = re.sub(r"-o\s+\S+\.o", "-o /tmp/res_iq3s.o", cmd)
cmd = cmd.replace(" -c ", " -c -Rpass-analysis=kernel-resource-usage ")
p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
out = p.stderr
print("rc", p.returncode, "chars", len(out))
open("/tmp/res_iq3s.txt","w").write(out)
PY
echo "=== remarks ==="
grep -c "kernel-resource-usage" /tmp/res_iq3s.txt || true
grep -A 6 "mul_mat_qIL9ggml_type21ELi64ELb0" /tmp/res_iq3s.txt | head -20
' 2>&1 | tail -30
''', t=1200))
