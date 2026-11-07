# 明确路径：从 config 原文 + 运行进程 argv + 进程实际打开的 fd 三处交叉确认
import base64, subprocess

SSH = ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
       "-o", "ServerAliveInterval=15", "albus@192.168.50.166"]
SC = r'''set -u
C=strata166-407
echo "===== A) config 原文（166 上的 LIVE）====="
cat /home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
echo
echo "===== B) 容器内两个进程的 argv ====="
docker exec $C sh -c 'for p in $(ls /proc | grep -E "^[0-9]+$"); do [ -r /proc/$p/cmdline ] || continue; c=$(tr "\0" " " < /proc/$p/cmdline); case "$c" in *server.py*) echo "serve  pid=$p : $c";; *build-906/strata*) echo "engine pid=$p : $c";; *strata-vision*) echo "vision pid=$p : $c";; esac; done'
echo
echo "===== C) 引擎进程实际打开的文件（fd 解析，去重）====="
docker exec $C sh -c 'EP=$(ps -ef | grep "[b]uild-906/strata" | awk "{print \$2}" | head -1); echo "engine pid=$EP"; ls -l /proc/$EP/fd 2>/dev/null | sed "s/.* -> //" | sort -u | grep -E "gguf|packs|mtp|vision|mmproj" | head -40'
echo
echo "===== D) 各路径实况 ====="
echo "--- 主模型：huihui 目录 ---"
ls -l /models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/
ls -l /models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/unsloth-UD-IQ4_XS/
echo "--- 主模型：pack ---"
ls -l /home/albus/strata166/data/packs/huihui-ud-iq4_xs/
echo "--- MTP ---"
ls -l /home/albus/strata166/data/mtp/
ls -l /home/albus/strata166/data/mtp/rt/
echo "--- vision ---"
ls -l /home/albus/strata166/data/vision/
echo
echo "===== E) vision 编码器进程 ====="
docker exec $C sh -c 'ps -ef | grep "[s]trata-vision" || echo "(未在跑；--vision 下由 serve 按需拉起/常驻)"'
echo
echo "===== F) 关键日志行（路径三处的原文佐证）====="
L=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
grep -nE 'engine started|PLE on|draft layer loaded|native pack|strata-vision|vision' "$L" | head -14
'''
p = subprocess.run(SSH + ["base64 -d | bash"], input=base64.b64encode(SC.encode()) + b"\n",
                   capture_output=True, timeout=600)
out = p.stdout.decode("utf-8", "replace")
open(r"D:/workbuddy_space/strata_ws/deploy/tmp/_w715_paths.txt", "w", encoding="utf-8", newline="\n").write(out)
print(out)
if p.stderr.strip():
    print("ERR:", p.stderr.decode("utf-8", "replace")[-300:])
