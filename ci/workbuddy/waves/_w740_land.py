# W709 步25：统一落盘确认（本机件 + 166 件 + 服务态）
import hashlib, io, os, sys
sys.path.insert(0, r'D:/workbuddy/_z_rk80')
import _sshutil

BAN = ['\u21d2', '\u2192', '\u2014', '\u2013', '\u2026', '\u2265', '\u2264', '\u2260', '\u2212', '\u00d7']

print('=== A) 本机交付件与固化件 ===')
LOCAL = [
    r'D:/strata166/W709_PARAM_OPTIMUM.md',
    r'D:/strata166/W709_HANDOVER.md',
    r'D:/strata166/params/PARAM_REGISTER.tsv',
    r'D:/strata166/params/gen_config.py',
    r'D:/strata166/params/verify_config.py',
    r'D:/strata166/params/generated/strata-ud-iq4_xs.json',
    r'D:/strata166/params/evidence/w709_calib_out.json',
    r'D:/strata166/params/_verify_w709b.txt',
    r'D:/workbuddy/.workbuddy/memory/2026-10-08.md',
]
for p in LOCAL:
    if not os.path.isfile(p):
        print('  %-56s ABSENT' % os.path.basename(p)); continue
    b = open(p, 'rb').read()
    t = b.decode('utf-8', 'replace')
    ban = {hex(ord(k)): t.count(k) for k in BAN if t.count(k)}
    print('  %-56s %8d B  md5=%s  CR=%d  BAN=%s' % (os.path.basename(p), len(b), hashlib.md5(b).hexdigest()[:16], b.count(b'\r'), ban or 'CLEAN'))

print()
print('=== B) A/B 原始输出（证据链）===')
for f in ['_pr131.out.txt', '_w726.out.txt', '_w731.out.txt', '_w732.out.txt', '_w733.out.txt',
          '_w736.out.txt', '_w727.out.txt']:
    p = r'D:/workbuddy/_z_rk81/' + f
    if not os.path.isfile(p):
        print('  %-18s ABSENT' % f); continue
    b = open(p, 'rb').read()
    print('  %-18s %8d B  md5=%s' % (f, len(b), hashlib.md5(b).hexdigest()[:16]))

print()
print('=== C) 166 终态 ===')
sc = r'''
echo "--- 容器 ---"; docker ps -a --format '{{.Names}}|{{.Status}}' | grep -i strata
echo "--- 服务 ---"; docker exec strata166-402 bash -lc 'curl -s -m 8 -o /dev/null -w "http=%{http_code}\n" http://127.0.0.1:8090/v1/models'
echo "--- LIVE config ---"; md5sum /home/albus/strata166/data/strata-ud-iq4_xs.json
echo "--- register（应 35 行 / a41545acaa35036afca1250d39a73f18）---"
md5sum /home/albus/strata166/params/PARAM_REGISTER.tsv
echo "--- 启动行三旋钮 ---"
grep "engine started" /home/albus/strata166/data/strata-ud-iq4_xs.log | tail -1 | grep -o -- '--pcie-frac [0-9.]*\|--spec-min-p [0-9.]*\|--prompt-cache-every [0-9]*'
echo "--- 残留 / 临时 ---"
pgrep -af '_w680|calibrate|run_calib|w709' | head -3 || echo "(无残留进程)"
docker ps -a --format '{{.Names}}' | grep -i calib || echo "(无临时容器)"
echo "--- 磁盘 / VRAM ---"; df -h / | tail -1; rocm-smi --showmeminfo vram 2>/dev/null | grep -i used
echo "--- 交接件是否已在 166（本波刚写，尚未同步 => 预期 ABSENT）---"
ls -la /home/albus/strata166/W709_HANDOVER.md 2>&1 | tail -1
'''
rc, out, err = _sshutil.run_remote(sc, timeout=300, host='192.168.50.166')
print(out)
if err.strip():
    print('STDERR:', err[:300])
