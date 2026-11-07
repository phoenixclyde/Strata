import subprocess, base64
def sh(s, t=420):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
L=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
prev=$(grep -ac "strata prefill timing" "$L")
cd /home/albus/strata166/tmp && python3 mt_reuse_phase.py
now=$(grep -ac "strata prefill timing" "$L")
echo "=== new timing lines: $((now-prev)) ==="
grep -a "strata prefill timing" "$L" | tail -n +$((prev+1)) | cut -c1-1000
''', t=400))
