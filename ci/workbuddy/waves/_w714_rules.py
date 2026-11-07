# 读 /models 的"规则"：README.md 全文 + 目录约定（只读）
import subprocess, base64

REMOTE = """set -u
echo '=== /models/README.md 全文 ==='
cat /models/README.md
echo
echo '=== /models 一级目录（发布者/仓库名约定）==='
for d in /models/*/; do
  n=$(ls -1 "$d" 2>/dev/null | head -3 | tr '\\n' ' ')
  echo "  $(basename $d) :: $n"
done
echo '=== 是否有与本模型相关的既有目录 ==='
find /models -maxdepth 3 -iname '*Qwen3.8*' -o -maxdepth 3 -iname '*Flash-Next*' 2>/dev/null | head -20
echo '=== /models 下是否已有 UD-IQ4_XS 或 mmproj ==='
find /models -maxdepth 4 -iname '*ud-iq4*' -o -maxdepth 4 -iname '*mmproj*' 2>/dev/null | head -20
echo '=== .msc / .lock 是什么（约定线索）==='
head -c 200 /models/.msc; echo; ls -la /models/.lock | head -5
"""
p = subprocess.run(["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
                    "albus@192.168.50.166", "base64 -d | bash"],
                   input=base64.b64encode(REMOTE.encode("utf-8")) + b"\n", capture_output=True, timeout=180)
print(p.stdout.decode("utf-8", "replace"))
if p.stderr.strip():
    print("STDERR:", p.stderr.decode("utf-8", "replace")[-400:])
