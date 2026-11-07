# 精确查现役 PLE/n-gram 状态 + 引擎启动头部 + vision 编译结果
import base64, subprocess

SSH = ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
       "-o", "ServerAliveInterval=15", "albus@192.168.50.166"]

SC = r'''set -u
L=/home/albus/strata166/data/strata-ud-iq4_xs.log
echo "===== 1) PLE / n-gram 精确命中 ====="
grep -inE 'PLE table|ple_reader|n-gram|per_layer_token|ple-key|ple_io|ple-io|PLE:' "$L" 2>/dev/null | head -20
echo "(命中 $(grep -icE 'PLE table|ple_reader|n-gram|per_layer_token' "$L" 2>/dev/null || true) 行)"
echo
echo "===== 2) 引擎启动头部（前 70 行）====="
head -70 "$L" 2>/dev/null
echo
echo "===== 3) vision 编译结果 ====="
tail -c 500 /home/albus/strata166/data/_vision_build.log 2>/dev/null
echo "--- 产物 ---"
ls -l /home/albus/strata166/data/vision/ 2>/dev/null || echo "(尚未生成)"
'''
p = subprocess.run(SSH + ["base64 -d | bash"], input=base64.b64encode(SC.encode()) + b"\n",
                   capture_output=True, timeout=600)
out = p.stdout.decode("utf-8", "replace")
open(r"D:/workbuddy_space/strata_ws/deploy/tmp/_w715_ple.txt", "w", encoding="utf-8", newline="\n").write(out)
print(out)
if p.stderr.strip():
    print("ERR:", p.stderr.decode("utf-8", "replace")[-400:])
