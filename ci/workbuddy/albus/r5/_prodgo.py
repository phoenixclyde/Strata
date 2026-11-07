import subprocess, base64
def sh(s, t=60):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
script = r'''
cat > /home/albus/strata166/tmp/prodchk.sh <<'EOS'
#!/bin/sh
cd /home/albus/strata166/tmp
OUT=/home/albus/strata166/data/w792_prodchk.txt
{
echo "=== prod M x2 (no instrumentation) $(date +%H:%M:%S) ==="
python3 w776_bench.py M 2 2>&1 | grep -E "run[12]|median"
echo "=== prod L x1 ==="
python3 w776_bench.py L 1 2>&1 | grep -E "run1|median"
echo "=== needle 32k d50 ==="
docker exec strata166-407 python3 /src/tools/needle_bench.py --lengths 32k --depths 50 --url http://127.0.0.1:8090 2>&1 | tail -2
echo "=== DONE $(date +%H:%M:%S) ==="
} > "$OUT" 2>&1
EOS
chmod +x /home/albus/strata166/tmp/prodchk.sh
(setsid nohup /home/albus/strata166/tmp/prodchk.sh >/dev/null 2>&1 </dev/null &) ; echo GO
'''
print(sh(script))
