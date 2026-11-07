import subprocess, base64
def sh(s, t=60):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
f=$(ls -t /home/albus/strata166/data/tune_rocblas_*.txt 2>/dev/null | head -1); echo FILE=$f
grep -c "^case " "$f" 2>/dev/null; grep -a -E "^best |^keep_default|^no_solutions|wrote " "$f" 2>/dev/null | tail -20
echo "=== proc ==="; ps -ef | grep -c "[t]une_rocblas"
'''))
