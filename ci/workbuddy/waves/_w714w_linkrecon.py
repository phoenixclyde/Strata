# 只读勘察：/weights 与 /models 的 inode/链接关系、/data/mtp 布局、/models 是否独立挂载
import base64, subprocess

SSH = ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
       "-o", "ServerAliveInterval=15", "albus@192.168.50.166"]
SC = r'''set -u
echo "=== A) /weights ==="
ls -li /home/albus/strata166/weights/ 2>/dev/null
echo
echo "=== B) /models/unsloth/Qwen3.8-Flash-Next-UD-IQ4_XS ==="
ls -li /models/unsloth/Qwen3.8-Flash-Next-UD-IQ4_XS/ 2>/dev/null
echo
echo "=== C) huihui 目录 ==="
ls -li /models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/ 2>/dev/null
ls -li /models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/unsloth-UD-IQ4_XS/ 2>/dev/null
echo
echo "=== D) /data/mtp 布局 ==="
ls -l /home/albus/strata166/data/mtp/ 2>/dev/null
echo "--- mtp/rt ---"
ls -l /home/albus/strata166/data/mtp/rt/ 2>/dev/null | head -12
echo "--- 体积 ---"
du -sh /home/albus/strata166/data/mtp 2>/dev/null
echo "--- inventory 自述 ---"
head -c 600 /home/albus/strata166/data/mtp/mtp-inventory.json 2>/dev/null; echo
echo
echo "=== E) 挂载与空间 ==="
findmnt -no SOURCE,FSTYPE,OPTIONS /models 2>/dev/null
findmnt -no SOURCE,FSTYPE,OPTIONS /home/albus/strata166/data 2>/dev/null
df -h /models /home | sed -n '1,6p'
echo
echo "=== F) 全盘查 mmproj / 00001 的所有副本（同 inode 归并）==="
find /models /home/albus/strata166 -maxdepth 6 \( -name 'mmproj-Qwen3.8*' -o -name 'Qwen3.8-Flash-Next-UD-IQ4_XS-00001*' \) -printf '%i %s %p\n' 2>/dev/null | sort
'''
p = subprocess.run(SSH + ["base64 -d | bash"], input=base64.b64encode(SC.encode()) + b"\n",
                   capture_output=True, timeout=300)
out = p.stdout.decode("utf-8", "replace")
open(r"D:/workbuddy_space/strata_ws/deploy/tmp/_w714_linkrecon.txt", "w", encoding="utf-8", newline="\n").write(out)
print(out)
if p.stderr.strip():
    print("ERR:", p.stderr.decode("utf-8", "replace")[-300:])
