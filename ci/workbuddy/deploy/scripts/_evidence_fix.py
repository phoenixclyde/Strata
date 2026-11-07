# -*- coding: utf-8 -*-
"""审计整改①：把缺失的原始证据重新取下来并【落盘】（审计 F2/F6/F9 指出的取证缺口）"""
import base64, os, subprocess

KEY = os.path.expanduser('~/.ssh/id_ed25519_workbuddy')
SSH = r'C:\Program Files\Git\usr\bin\ssh.exe'
HOST = 'albus@192.168.50.166'

SCRIPT = r'''
set +e
echo "########## A. 构建期物证（审计 F6 指出的缺口）##########"
echo "--- CMakeCache 关键项 ---"
docker exec strata166 bash -lc 'grep -E "^STRATA_(ENABLE_CUDA|ENABLE_HIP|HIP_GFX906|PREFILL_MMQ|MMQ_KQUANTS|NATIVE_EXPERTS)" /src/build-906/CMakeCache.txt'
echo "--- libstrata_mmq.a ---"
docker exec strata166 bash -lc 'ls -l /src/build-906/libstrata_mmq.a; echo -n "bytes="; stat -c %s /src/build-906/libstrata_mmq.a'
echo "--- mmq 符号数 ---"
docker exec strata166 bash -lc 'echo -n "mmq_sym_total="; nm -C /src/build-906/strata 2>/dev/null | grep -c "mmq"; echo -n "prefill_mmq_ns="; nm -C /src/build-906/strata 2>/dev/null | grep -c "strata::prefill::mmq"'
echo
echo "########## B. #420 回退提示：源码定义点 + 全日志检索（审计 F6 第 3 项）##########"
echo "--- 源码里的提示原文（本机已核，此处打印 166 侧同源文件）---"
docker exec strata166 bash -lc 'grep -n "prompt kernels" /src/src/prefill/moe_mmq.cu 2>/dev/null || echo "(容器内无 src 源码树，改用本机副本)"'
echo "--- 全容器日志检索（stdout+stderr 同写 /data/*.log）---"
docker exec strata166 bash -lc 'echo -n "logs_total_lines="; cat /data/*.log 2>/dev/null | wc -l; echo -n "hit_tile=";  cat /data/*.log 2>/dev/null | grep -ci "no tile" ; echo -n "hit_promptkernels="; cat /data/*.log 2>/dev/null | grep -ci "prompt kernels"; echo -n "hit_nonmmq="; cat /data/*.log 2>/dev/null | grep -ci "non-MMQ"; echo -n "hit_mmq_any="; cat /data/*.log 2>/dev/null | grep -ci "mmq"'
echo
echo "########## C. 当前运行态（审计 F9：把 ctx 一并落盘）##########"
docker exec strata166 bash -lc 'curl -s -m 10 http://127.0.0.1:8090/v1/models; echo'
docker exec strata166 bash -lc 'python3 -c "
import json;a=json.load(open(\"/data/strata-ud-q4_k_xl.json\"))[\"args\"];print(\"ARGS\", \" \".join(map(str,a)))"'
echo
echo "########## D. SSD 队列深度扫描【重跑并留痕】（审计 F2 指出的缺口）##########"
cat > /home/albus/strata166/data/qd2.py <<'PYEOF'
import os, mmap, random, time, threading
P = '/weights/Qwen3.8-Flash-Next-UD-Q4_K_XL-00003-of-00004.gguf'
sz = os.path.getsize(P); BS = 4096; TOT = 4000
def worker(fd, offs, out, idx):
    buf = mmap.mmap(-1, BS); lat = []
    for off in offs:
        t = time.perf_counter(); os.preadv(fd, [buf], off); lat.append(time.perf_counter() - t)
    out[idx] = lat
print('file=%s size=%d' % (P, sz))
for qd in (1, 4, 16, 64):
    per = TOT // qd
    fd = os.open(P, os.O_RDONLY | os.O_DIRECT)
    offs = [random.randrange(0, (sz - BS) // BS) * BS for _ in range(TOT)]
    out = [None] * qd
    ths = [threading.Thread(target=worker, args=(fd, offs[i*per:(i+1)*per], out, i)) for i in range(qd)]
    t0 = time.perf_counter()
    for t in ths: t.start()
    for t in ths: t.join()
    dt = time.perf_counter() - t0
    os.close(fd)
    lat = sorted(x for l in out if l for x in l); n = len(lat)
    print('QD=%-3d n=%-5d %8.0f IOPS  %7.2f MB/s  p50=%6.0fus  p95=%7.0fus  mean=%6.0fus'
          % (qd, n, n/dt, n*BS/dt/1e6, lat[n//2]*1e6, lat[int(n*0.95)]*1e6, sum(lat)/n*1e6))
# 顺序读
fd = os.open(P, os.O_RDONLY | os.O_DIRECT); bs = 8 << 20; buf = mmap.mmap(-1, bs); r = []
for i in range(3):
    off = random.randrange(0, (sz - bs) // 4096) * 4096
    t = time.perf_counter(); os.preadv(fd, [buf], off); r.append(bs/(time.perf_counter()-t)/1e6)
os.close(fd)
print('SEQ8MB_MBps = %.0f / %.0f / %.0f' % tuple(r))
PYEOF
docker exec strata166 python3 -u /data/qd2.py 2>&1
echo
echo "########## E. 盘与文件系统（补齐语境）##########"
sudo -n hdparm -I /dev/sda 2>/dev/null | egrep -i "Model Number|Firmware" | head -3
findmnt -no SOURCE,FSTYPE / 2>/dev/null
docker exec strata166 bash -lc 'uname -r; cat /etc/os-release 2>/dev/null | head -2'
'''

b64 = base64.b64encode(SCRIPT.encode('utf-8')).decode('ascii')
cmd = [SSH, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-i', KEY, HOST, 'base64 -d | bash']
r = subprocess.run(cmd, input=b64.encode('ascii'), capture_output=True, timeout=1800)
out = r.stdout.decode('utf-8', 'replace')
if r.stderr.strip():
    out += '\n--- STDERR ---\n' + r.stderr.decode('utf-8', 'replace')[:600]
with open(r'D:\strata166\logs\_evidence_166.txt', 'w', encoding='utf-8') as f:
    f.write(out)
print(out)
print('SAVED -> D:\\strata166\\logs\\_evidence_166.txt')
