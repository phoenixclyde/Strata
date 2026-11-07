# 逐条显式 cp（无循环/无嵌套引号）：把 3 分片真拷贝到 /models，后台 nohup + 日志
import base64, subprocess, time

SSH = ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
       "-o", "ServerAliveInterval=15", "albus@192.168.50.166"]
S = "/home/albus/strata166/weights"
D = "/models/unsloth/Qwen3.8-Flash-Next-UD-IQ4_XS"
F1 = "Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf"
F2 = "Qwen3.8-Flash-Next-UD-IQ4_XS-00002-of-00003.gguf"
F3 = "Qwen3.8-Flash-Next-UD-IQ4_XS-00003-of-00003.gguf"

SCRIPT = """set -u
W=/home/albus/strata166/w712
D='%s'
S='%s'
if pgrep -f 'cp --remove-destination' >/dev/null; then echo ALREADY; exit 0; fi
cat > "$W/modelcopy2.sh" <<'EOS'
#!/usr/bin/env bash
set -u
S='%s'
D='%s'
for f in %s %s %s; do
  echo "[$(date +%%F %%T)] copy $f"
  rm -f "$D/$f"
  cp --remove-destination "$S/$f" "$D/$f" || { echo "FAIL $f"; exit 1; }
  a=$(stat -c %%s "$S/$f"); b=$(stat -c %%s "$D/$f")
  echo "  size src=$a dst=$b  $([ "$a" = "$b" ] && echo SIZE_OK || echo SIZE_MISMATCH)"
done
echo COPY2_DONE
EOS
chmod +x "$W/modelcopy2.sh"
setsid nohup bash "$W/modelcopy2.sh" > "$W/modelcopy2.log" 2>&1 < /dev/null &
sleep 6
echo '--- 进程 ---'; pgrep -af modelcopy2 | head -2 || echo NO_PROC
echo '--- 日志 ---'; cat "$W/modelcopy2.log"
""" % (D, S, S, D, F1, F2, F3)

p = subprocess.run(SSH + ["base64 -d | bash"], input=base64.b64encode(SCRIPT.encode()) + b"\n",
                   capture_output=True, timeout=300)
print(p.stdout.decode("utf-8", "replace"))
if p.stderr.strip():
    print("STDERR:", p.stderr.decode("utf-8", "replace")[-300:])
