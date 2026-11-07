# 侦察 3（只读）：166 的 /models 与 /weights 现状 + 新旧文件对账
import os, subprocess, base64, hashlib

print("=== 本机新下载：文件名/大小/md5（分片1 与 mmproj）===")
D = r"D:/Qwen3.8-Flash-Next-UD-IQ4_XS"
for f in sorted(os.listdir(D)):
    fp = os.path.join(D, f)
    if os.path.isfile(fp):
        sz = os.path.getsize(fp)
        if sz < 200_000_000:      # 只对小件算 md5（大件下面在 166 侧比）
            h = hashlib.md5(open(fp, "rb").read()).hexdigest()
            print("  %-56s %14.2f MB  md5=%s" % (f, sz / 1e6, h))
        else:
            print("  %-56s %14.2f MB  (大件，跳过本机 md5)" % (f, sz / 1e6))

REMOTE = """set -u
echo '=== 166: /models 是否存在（用户要求放这里）==='
if [ -d /models ]; then ls -la /models | head -15; du -sh /models 2>/dev/null; else echo '(不存在)'; fi
echo '=== 166: /home/albus/strata166/weights（现役 native 目录）==='
ls -l /home/albus/strata166/weights/ | head -15
echo '=== 166: weights 里 0.01GB 那片与 mmproj 的 md5（对新下载对账用）==='
for f in /home/albus/strata166/weights/*00001-of-00003.gguf /home/albus/strata166/weights/mmproj*.gguf; do
  [ -f "$f" ] && md5sum "$f"
done
echo '=== 166: 是否已有过 vision 相关件 ==='
ls -l /home/albus/strata166/weights/ /home/albus/strata166/data/ 2>/dev/null | grep -i mmproj || echo '(166 上无 mmproj)'
echo '=== 166: data/packs 里的 native_experts / 关键小件 ==='
ls -l /home/albus/strata166/data/packs/ud-iq4_xs/ | head -12
echo '=== 166 传输落地盘余量 ==='
df -h /home | tail -1
echo '=== 本机 -> 166 通道自测（不上传数据）==='
echo ping_ok
"""
p = subprocess.run(["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
                    "albus@192.168.50.166", "base64 -d | bash"],
                   input=base64.b64encode(REMOTE.encode("utf-8")) + b"\n", capture_output=True, timeout=180)
print()
print(p.stdout.decode("utf-8", "replace"))
if p.stderr.strip():
    print("STDERR:", p.stderr.decode("utf-8", "replace")[-300:])
