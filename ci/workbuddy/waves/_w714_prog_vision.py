# 拷贝进度 + vision 段的确切写法（setup.py 里怎么写进 config）
import io, os, subprocess, base64

WS = r"D:/workbuddy_space/strata_ws"
SSH = ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
       "-o", "ServerAliveInterval=15", "albus@192.168.50.166"]


def run(script, t=300):
    p = subprocess.run(SSH + ["base64 -d | bash"], input=base64.b64encode(script.encode()) + b"\n",
                       capture_output=True, timeout=t)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


print("=== A) 拷贝进度 ===")
rc, out, err = run("""set -u
D=/models/unsloth/Qwen3.8-Flash-Next-UD-IQ4_XS
echo '--- 进程 ---'; pgrep -af 'cp -f /home/albus/strata166/weights' | head -2 || echo NO_CP
echo '--- 日志 ---'; cat /home/albus/strata166/w712/modelcopy.log 2>/dev/null | tail -3
echo '--- 目标目录大小 ---'; du -sb "$D" 2>/dev/null | cut -f1
du -sh "$D" 2>/dev/null
echo '--- 各文件 ---'; ls -l "$D" | tail -5
echo '--- 链接数 ---'; stat -c '%h %s %n' "$D"/*.gguf
echo '--- 盘 ---'; df -h /home | tail -1
""", 300)
print(out)
if err.strip():
    print("ERR:", err.strip()[-200:])

print("=== B) setup.py 里 vision 段怎么写入 config ===")
B = r"D:/workbuddy_space/strata_ws/deploy/tmp/src411/Strata-0.1.41"
L = io.open(os.path.join(B, "setup.py"), encoding="utf-8", errors="replace").read().splitlines()
shown = 0
for i, l in enumerate(L):
    if ('["vision"]' in l or "'vision'" in l and 'cfg' in l or 'vision" :' in l or
            'vision": {' in l or 'def vision' in l or 'mmproj' in l and 'cfg' in l):
        for j in range(max(0, i - 8), min(i + 14, len(L))):
            print("  %5d %s" % (j + 1, L[j][:150]))
        print("  ---")
        shown += 1
        if shown >= 4:
            break
if not shown:
    print("  (未命中；改搜 mmproj 写 config 的位置)")
    for i, l in enumerate(L):
        if 'mmproj' in l and ('=' in l or ':' in l):
            print("  %5d %s" % (i + 1, l[:150]))
            shown += 1
            if shown > 15:
                break
