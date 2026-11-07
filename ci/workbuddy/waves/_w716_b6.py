# B6：源码判定 STRATA_MMVQ_IL 在本机(gfx906)是否命中；并盘点 166 上可用的基准探针
import base64, subprocess

SSH = ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
       "-o", "ServerAliveInterval=15", "albus@192.168.50.166"]
SC = r'''set -u
C=strata166-407
echo "===== A) MMVQ_IL 在源码里的落点 ====="
docker exec $C sh -c 'grep -rn "MMVQ_IL\|mmvq_il" /src/src /src/include 2>/dev/null | head -30'
echo
echo "===== B) g_mmvq_il() / native_mmvq_il_supported() 定义 ====="
docker exec $C sh -c 'grep -rn -A12 "bool g_mmvq_il\|g_mmvq_il()" /src/src /src/include 2>/dev/null | head -50'
echo
echo "===== C) native_mmvq_il_supported 的判定条件 ====="
docker exec $C sh -c 'grep -rn -B2 -A25 "native_mmvq_il_supported" /src/src /src/include 2>/dev/null | head -70'
echo
echo "===== D) help 里 MMVQ_IL 的原文 ====="
docker exec $C /src/build-906/strata --help 2>&1 | grep -i -B2 -A4 'mmvq' | head -30
echo
echo "===== E) 166 上的基准探针（/data/*.py）====="
ls -l /home/albus/strata166/data/*.py 2>/dev/null
echo "--- 各脚本首两行说明 ---"
for f in /home/albus/strata166/data/bench*.py /home/albus/strata166/data/ab.py; do
  [ -f "$f" ] || continue
  echo "== $(basename $f)"
  head -4 "$f" | sed 's/^/   /'
done
'''
p = subprocess.run(SSH + ["base64 -d | bash"], input=base64.b64encode(SC.encode()) + b"\n",
                   capture_output=True, timeout=600)
out = p.stdout.decode("utf-8", "replace")
open(r"D:/workbuddy_space/strata_ws/deploy/tmp/_w716_b6.txt", "w", encoding="utf-8", newline="\n").write(out)
print(out)
if p.stderr.strip():
    print("ERR:", p.stderr.decode("utf-8", "replace")[-300:])
