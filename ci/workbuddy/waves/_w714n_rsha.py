# 166 上对现役三片跑全量 sha256（钉死 base vs huihui），后台长跑
import base64, subprocess, time

SSH = ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
       "-o", "ServerAliveInterval=15", "albus@192.168.50.166"]
SC = r'''set -u
D=/models/unsloth/Qwen3.8-Flash-Next-UD-IQ4_XS
echo "START $(date -Is)"
for f in "$D"/Qwen3.8-Flash-Next-UD-IQ4_XS-0000*.gguf; do
  t0=$(date +%s)
  h=$(sha256sum "$f" | cut -d' ' -f1)
  t1=$(date +%s)
  echo "$(basename "$f")  sha256=$h  ($((t1-t0))s)"
done
echo "DONE $(date -Is)"
'''
t0 = time.time()
p = subprocess.run(SSH + ["base64 -d | bash"], input=base64.b64encode(SC.encode()) + b"\n",
                   capture_output=True, timeout=3600)
out = p.stdout.decode("utf-8", "replace")
open(r"D:/workbuddy_space/strata_ws/deploy/tmp/_w714_rsha166.txt", "w", encoding="utf-8", newline="\n").write(out)
print(out)
if p.stderr.strip():
    print("ERR:", p.stderr.decode("utf-8", "replace")[-400:])
print("elapsed=%.0fs" % (time.time() - t0))
