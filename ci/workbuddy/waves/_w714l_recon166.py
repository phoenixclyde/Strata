# 只读勘察：166 上 /models 与 /weights 的实际归属（inode/抽样哈希/现役容器指向/空间）
import base64, subprocess

SSH = ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
       "-o", "ServerAliveInterval=15", "albus@192.168.50.166"]

SC = r'''set -u
echo "=== A) /models 树 + inode/link ==="
ls -li /models 2>/dev/null
echo "--- /models/*/ ---"
for d in /models/*/; do echo "[$d]"; ls -li "$d" 2>/dev/null; done
echo "--- /models/*/*/ ---"
for d in /models/*/*/; do echo "[$d]"; ls -li "$d" 2>/dev/null; done
echo
echo "=== B) /weights 现状 ==="
ls -li /home/albus/strata166/weights/ 2>/dev/null
echo
echo "=== C) 抽样 md5（head / mid / tail 各 16MB）；对撞基准 = 本机 D 盘那份(huihui) ==="
for f in /models/unsloth/*/*.gguf /models/unsloth/*.gguf /models/huihui-ai/*/*.gguf /models/huihui-ai/*/*/*.gguf /home/albus/strata166/weights/*.gguf; do
  [ -f "$f" ] || continue
  sz=$(stat -c %s "$f")
  if [ "$sz" -lt 40000000 ]; then
    echo "-- $f  ($sz)  [小件, 全量 sha256]"
    echo "   sha256: $(sha256sum "$f" | cut -d' ' -f1)"
    continue
  fi
  mid=$(( sz / 2 / 1048576 ))
  echo "-- $f  ($sz)"
  echo "   head: $(dd if="$f" bs=1M count=16 2>/dev/null | md5sum | cut -d' ' -f1)"
  echo "   mid : $(dd if="$f" bs=1M skip=$mid count=16 2>/dev/null | md5sum | cut -d' ' -f1)"
  echo "   tail: $(tail -c 16777216 "$f" | md5sum | cut -d' ' -f1)"
done
echo
echo "=== D) 容器 ==="
docker ps -a --format '{{.Names}} | {{.Image}} | {{.Status}} | {{.Ports}}'
echo "--- 现役相关 inspect ---"
for c in strata166-406 strata166-405 strata166-404 strata166-403; do
  if docker inspect "$c" >/dev/null 2>&1; then
    echo "$c :: $(docker inspect -f 'status={{.State.Status}} image={{.Config.Image}} binds={{json .HostConfig.Binds}}' "$c")"
  fi
done
echo "--- LIVE config 指向 ---"
head -c 700 /home/albus/strata166/data/strata-ud-iq4_xs.json 2>/dev/null; echo
echo
echo "=== E) 空间 ==="
df -h /home /models / 2>/dev/null | sed -n '1,12p'
'''
p = subprocess.run(SSH + ["base64 -d | bash"], input=base64.b64encode(SC.encode()) + b"\n",
                   capture_output=True, timeout=900)
out = p.stdout.decode("utf-8", "replace")
open(r"D:/workbuddy_space/strata_ws/deploy/tmp/_w714_recon166.txt", "w", encoding="utf-8", newline="\n").write(out)
print(out)
if p.stderr.strip():
    print("ERR:", p.stderr.decode("utf-8", "replace")[-500:])
