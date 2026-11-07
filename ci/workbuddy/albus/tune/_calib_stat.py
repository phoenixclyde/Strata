import subprocess, base64

HOST = "albus@192.168.50.166"
SH = r'''
cd /home/albus/strata166
echo "===LINES==="
wc -l data/calib.out
echo "===TAIL==="
tail -14 data/calib.out
echo "===GPU==="
/opt/rocm/bin/rocm-smi --showuse 2>/dev/null | grep -i "use"
echo "===PS==="
docker ps --format "{{.Names}}|{{.Status}}" | head -5
'''
p = subprocess.run(["ssh", "-o", "BatchMode=yes", HOST, "base64 -d | bash"],
                   input=base64.b64encode(SH.encode()).decode("ascii").encode("ascii"),
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
print(p.stdout.decode("utf-8", "replace"))
