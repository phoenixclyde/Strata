import subprocess, base64
HOST = "albus@192.168.50.166"
SH = r'''
L=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
echo "===LAST_START_LINE_NO==="
n=$(grep -n "engine started" $L | tail -1 | cut -d: -f1); echo $n
echo "===SINCE==="
tail -n +$n $L | grep -E "pool workers|aux cpus|VRAM free with everything|expert cache auto|expert cache [0-9]+ slots|below 512|prefill chunk|resident RAM mode|prefill plan|vram-reserve|reserve" | head -14
echo "===ENGINE_CMD==="
tail -n +$n $L | grep "engine started" | head -1 | tr ' ' '\n' | grep -A1 -E "pool-workers|vram-reserve-mib" | head -8
echo "===WARNCOUNT==="
tail -n +$n $L | grep -c "below 512 MiB"
'''
b64 = base64.b64encode(SH.encode()).decode("ascii")
p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10",HOST,"base64 -d | bash"],
                   input=b64.encode("ascii"), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
print(p.stdout.decode("utf-8","replace")); print(p.stderr.decode("utf-8","replace")[:300])
