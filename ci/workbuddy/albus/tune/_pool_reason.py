import subprocess, base64
HOST = "albus@192.168.50.166"
SH = r'''
L=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
echo "===pool default line (historical)==="
grep -n "workers by default" $L | tail -6
echo "===CPU pool tasks/phase==="
grep -n "CPU pool tasks/phase" $L | tail -4
echo "===host-core lines==="
grep -n "host-core\|host thread on" $L | tail -6
echo "===callback warmup==="
grep -c "host-callback thread started" $L
'''
b64 = base64.b64encode(SH.encode()).decode("ascii")
p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10",HOST,"base64 -d | bash"],
                   input=b64.encode("ascii"), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
print(p.stdout.decode("utf-8","replace"))
