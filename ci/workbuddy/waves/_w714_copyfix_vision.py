# A) 修正拷贝：先删硬链接（不丢数据，源 /weights 仍在）再真拷贝，后台跑
# B) 查镜像里有没有 strata-vision + setup.py 怎么写 vision 段
import io, os, subprocess, base64

SSH = ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
       "-o", "ServerAliveInterval=15", "albus@192.168.50.166"]


def run(script, t=300):
    p = subprocess.run(SSH + ["base64 -d | bash"], input=base64.b64encode(script.encode()) + b"\n",
                       capture_output=True, timeout=t)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


print("=== A) 修正拷贝（rm 硬链接 + cp --remove-destination）===")
rc, out, err = run("""set -u
D=/models/unsloth/Qwen3.8-Flash-Next-UD-IQ4_XS
S=/home/albus/strata166/weights
W=/home/albus/strata166/w712
for f in Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf Qwen3.8-Flash-Next-UD-IQ4_XS-00002-of-00003.gguf Qwen3.8-Flash-Next-UD-IQ4_XS-00003-of-00003.gguf; do
  [ "$D/$f" -ef "$S/$f" ] && rm -f "$D/$f"          # 只删 /models 侧那个硬链接名，源文件不动
done
echo '--- rm 后链接数（源应仍为 1）---'; stat -c '%h %s %n' "$S"/*.gguf
if pgrep -f 'cp --remove-destination' >/dev/null; then echo ALREADY; else
  setsid nohup bash -c "for f in Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf Qwen3.8-Flash-Next-UD-IQ4_XS-00002-of-00003.gguf Qwen3.8-Flash-Next-UD-IQ4_XS-00003-of-00003.gguf; do cp --remove-destination \\"$S/$f\\" \\"$D/$f\\" || exit 1; done; echo COPY_DONE" > "$W/modelcopy.log" 2>&1 < /dev/null &
  sleep 6
fi
echo '--- 进程 ---'; pgrep -af 'cp --remove-destination' | head -2 || echo NO_CP
echo '--- 日志 ---'; tail -2 "$W/modelcopy.log" 2>/dev/null
echo '--- 目标 ---'; ls -l "$D" | tail -4; stat -c '%h %n' "$D"/*.gguf
echo '--- 盘 ---'; df -h /home | tail -1
""", 300)
print(out)
if err.strip():
    print("ERR:", err.strip()[-200:])

print("=== B) 镜像里有没有 strata-vision / 相关目标 ===")
rc2, out2, _ = run("""set -u
docker run --rm --entrypoint bash strata-gfx906:0.1.41 -lc 'ls -l /src/build-906/ | head -20; echo ---; ls /src/build-906/*vision* 2>/dev/null || echo "(无 vision 二进制)"; echo ---; ls /src/serve/ | head -20'
""", 300)
print(out2)
