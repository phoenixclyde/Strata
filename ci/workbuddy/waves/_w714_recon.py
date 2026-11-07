# 侦察 2（只读）：新下载目录全清单（含小文件/说明） + 166 现有模型布局 + B3c 结果
import os, subprocess, base64, time

D = r"D:/Qwen3.8-Flash-Next-UD-IQ4_XS"
print("=== 新下载目录全清单：%s ===" % D)
tot = 0
for dp, dn, fn in os.walk(D):
    for f in sorted(fn):
        fp = os.path.join(dp, f)
        try:
            sz = os.path.getsize(fp)
        except OSError:
            sz = -1
        tot += max(sz, 0)
        print("  %12.2f MB  %s%s" % (sz / 1e6, os.path.relpath(fp, D), "   <== 小文件/可能是说明" if sz < 5e6 else ""))
print("  合计 %.2f GB" % (tot / 1e9))
print("  子目录:", dn if 'dn' in dir() else os.listdir(D))

REMOTE = """set -u
echo '=== 166: /models 是否存在 ==='
ls -la /models 2>&1 | head -12
echo '=== 166: /home/albus/strata166/weights（现役 native 所在）==='
ls -l /home/albus/strata166/weights/ 2>&1 | head -12
du -sh /home/albus/strata166/weights 2>/dev/null
echo '=== 166: packs / mtp / data 顶层 ==='
ls -l /home/albus/strata166/data/ | head -20
du -sh /home/albus/strata166/data/packs/* /home/albus/strata166/data/mtp/* 2>/dev/null
echo '=== 磁盘 ==='
df -h / /home | tail -3
echo '=== 容器挂载（现役 -405）==='
docker inspect strata166-405 --format '{{json .HostConfig.Binds}}'
echo '=== LIVE config 的 args 与 vision 段 ==='
python3 -c "import json,io;c=json.load(io.open('/home/albus/strata166/data/strata-ud-iq4_xs.json',encoding='utf-8'));print('args:',' '.join(c['args']));print('vision:',c.get('vision'));print('has_mmproj_in_args:', any('mmproj' in str(x) for x in c['args']))"
echo '=== B3c 结果（md5 表 + 机制）==='
grep -E 'C1 |机制：|########## ARM' /home/albus/strata166/w712/b3c.log | tail -22
echo '=== B3c 收尾标记 ==='
grep -c 'B3c 收尾完毕' /home/albus/strata166/w712/b3c.log
"""
p = subprocess.run(["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
                    "albus@192.168.50.166", "base64 -d | bash"],
                   input=base64.b64encode(REMOTE.encode("utf-8")) + b"\n", capture_output=True, timeout=180)
print()
print(p.stdout.decode("utf-8", "replace"))
if p.stderr.strip():
    print("STDERR:", p.stderr.decode("utf-8", "replace")[-300:])
