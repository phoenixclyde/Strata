# 步骤2：切到 -406 -> 复验 -> 处理 /weights（删真实文件，改留指向 /models 的符号链接以保住旧容器回滚能力）
import base64, hashlib, os, subprocess, time

WS = r"D:/workbuddy_space/strata_ws"
PY = r"C:/Users/clyde/.workbuddy/binaries/python/versions/3.13.12/python.exe"
SSH = ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
       "-o", "ServerAliveInterval=15", "albus@192.168.50.166"]


def run(script, t=900):
    p = subprocess.run(SSH + ["base64 -d | bash"], input=base64.b64encode(script.encode()) + b"\n",
                       capture_output=True, timeout=t)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


print("=== 1) 切换 -405 -> -406（通用脚本，自带自动回滚）===")
rc, out, err = run("bash /home/albus/strata166/w712/switch_strata.sh strata166-406; echo SWITCH_RC=$?", 900)
print(out)
if err.strip():
    print("ERR:", err.strip()[-300:])

print("=== 2) 复验（本机 verify_config.py）===")
r = subprocess.run([PY, "-u", os.path.join(WS, "deploy", "params", "verify_config.py")],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
vl = [x for x in (r.stdout or "").splitlines() if "PASS=" in x or x.startswith("目标容器") or "P01" in x]
print("rc=%d | %s" % (r.returncode, " | ".join(vl)))

print("=== 3) 冒烟 + 引擎启动行确认 /models 路径 ===")
rc, out, err = run("""set -u
curl -s -m 8 http://127.0.0.1:8090/v1/models | head -c 120; echo
curl -s -m 8 -o /dev/null -w 'chat_http=%{http_code}\\n' -H 'Content-Type: application/json' \
  -d '{"model":"qwen3.8-flash-next-ud-iq4_xs","messages":[{"role":"user","content":"Reply OK"}],"max_tokens":8}' \
  http://127.0.0.1:8090/v1/chat/completions
N=$(grep -n 'engine started' /home/albus/strata166/data/strata-ud-iq4_xs.log | tail -1 | cut -d: -f1)
sed -n "${N}p" /home/albus/strata166/data/strata-ud-iq4_xs.log | grep -o -- '--native [^ ]*'
""", 300)
print(out)
if err.strip():
    print("ERR:", err.strip()[-300:])

print("=== 4) 处理 /weights：删真实文件 + 留符号链接往 /models（保旧容器回滚）===")
rc, out, err = run("""set -u
W=/home/albus/strata166/weights
D=/models/unsloth/Qwen3.8-Flash-Next-UD-IQ4_XS
echo '--- 删前 ---'; du -sh "$W" 2>/dev/null; ls -l "$W" | head -5; df -h /home | tail -1
rm -f "$W"/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf \
      "$W"/Qwen3.8-Flash-Next-UD-IQ4_XS-00002-of-00003.gguf \
      "$W"/Qwen3.8-Flash-Next-UD-IQ4_XS-00003-of-00003.gguf
rmdir "$W" 2>/dev/null || true
ln -sfn "$D" "$W"
echo '--- 删后 ---'; ls -l "$W"; du -sh "$D" 2>/dev/null; df -h /home | tail -1
echo '--- 符号链接能读到文件吗 ---'; ls -l "$W"/ | tail -5
""", 600)
print(out)
if err.strip():
    print("ERR:", err.strip()[-300:])

print("=== 5) 再复验一次（删 weights 之后）===")
r = subprocess.run([PY, "-u", os.path.join(WS, "deploy", "params", "verify_config.py")],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
print([x for x in (r.stdout or "").splitlines() if "PASS=" in x or x.startswith("目标容器")])
