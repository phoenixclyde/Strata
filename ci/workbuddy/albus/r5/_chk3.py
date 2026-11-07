import subprocess, base64
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
date +%H:%M:%S
ps -ef | grep -E "[p]f_run|[w]776_bench" | head
f=$(ls -t /home/albus/strata166/data/r5_pf_*.txt | head -1); echo FILE=$f; tail -6 "$f"
echo "=== last log lines ==="
grep -a "strata prefill timing" /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log | tail -2 | cut -c1-260
'''))
