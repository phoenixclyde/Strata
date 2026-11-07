# W709 步28：更新交接件指纹 + 同步到 166
import hashlib, io, os, sys
sys.path.insert(0, r'D:/workbuddy/_z_rk80')
import _sshutil

def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()

REG = r'D:/strata166/params/PARAM_REGISTER.tsv'
HO = r'D:/strata166/W709_HANDOVER.md'
new_md5 = md5(REG)
print('register 新 md5 =', new_md5)

# --- 更新交接件里的 register 指纹 ---
t = io.open(HO, encoding='utf-8').read()
old = 'md5 `a41545acaa35036afca1250d39a73f18`'
new = 'md5 `%s`' % new_md5
if old in t:
    assert t.count(old) == 1
    t = t.replace(old, new)
    print('交接件已更新 register 指纹')
else:
    print('!! 未找到旧指纹串，需人工核')

# 追加"落盘修复"小节（诚实记录本波自查出的四点）
ADD = """

---

## 7 本波落盘修复（收口时自查出的 4 点，已修）

| # | 问题 | 处置 |
|---|---|---|
| 1 | `PARAM_REGISTER.tsv` 含 2 个禁用码位（`3×3` 的 `×`、P32 行的 `⇒`） | 已清（改动 2 行），现 **BAN=CLEAN** |
| 2 | `gen_config.py`(1 行) / `verify_config.py`(3 行) 的破折号 | 已清，现 **BAN=CLEAN** |
| 3 | 记忆日志 `2026-10-08.md` 的**本波增量段**（`## W709a` 起）含 `⇒`×1 + `—`×12 | 已清（改动 7 行）；**更早段落的存量命中单独报出，非本波缺陷** |
| 4 | 本机 `params/evidence/` 缺 `w709_calib_out.json`（此前只推到了 166） | 已补本机副本（`5a39b6a08bc92d25073fb960f007d08f`） |

修复自证判据（首版判据有缺陷，已换）：
首版用「反向 undo 必须逐字节等于原文」——但 `-` 的反向映射**不唯一**（可能来自 `–`/`−`），
undo 会把所有连字符变成减号 ⇒ 断言必然失败。**是判据本身有缺陷，不是文件有问题。**
现判据三条：① 改后无禁用码位；② 行数不变且 `equal` 块逐行字节相同；
③ `replace` 块里每对 (old,new) 满足 `new == 对 old 施加同一张替换表`，且 **old 行必含至少一个禁用码位**。
"""
t = t.rstrip('\n') + ADD + '\n'
bb = t.encode('utf-8')
open(HO, 'wb').write(bb)
print('交接件 %d B md5=%s CR=%d' % (len(bb), md5(HO), bb.count(b'\r')))

# --- 同步 166 ---
print()
for lp, rp in [
    (REG, '/home/albus/strata166/params/PARAM_REGISTER.tsv'),
    (r'D:/strata166/params/gen_config.py', '/home/albus/strata166/params/gen_config.py'),
    (r'D:/strata166/params/verify_config.py', '/home/albus/strata166/params/verify_config.py'),
    (r'D:/strata166/params/evidence/w709_calib_out.json', '/home/albus/strata166/params/evidence/w709_calib_out.json'),
    (HO, '/home/albus/strata166/W709_HANDOVER.md'),
]:
    ok, size, m, det = _sshutil.push_b64(lp, rp)
    print('  push %-28s ok=%s size=%s md5=%s' % (os.path.basename(lp), ok, size, m))

sc = r'''
echo "--- 166 侧复验 ---"
md5sum /home/albus/strata166/params/PARAM_REGISTER.tsv /home/albus/strata166/W709_HANDOVER.md
python3 -c "
import io,collections,hashlib
p='/home/albus/strata166/params/PARAM_REGISTER.tsv'
b=open(p,'rb').read(); L=io.open(p,encoding='utf-8').read().splitlines()
print('  行数(不含表头) =', len(L)-1)
print('  status =', dict(collections.Counter(x.split(chr(9))[5] for x in L[1:] if x.strip())))
BAN=['\u21d2','\u2192','\u2014','\u2013','\u2026','\u2265','\u2264','\u2260','\u2212','\u00d7']
t=b.decode('utf-8')
print('  BAN =', {hex(ord(k)):t.count(k) for k in BAN if t.count(k)} or 'CLEAN', ' CR=', b.count(b'\r'))
"
echo "--- 服务仍在 ---"
docker ps --format '{{.Names}}|{{.Status}}' | grep strata166-402
docker exec strata166-402 bash -lc 'curl -s -m 8 -o /dev/null -w "http=%{http_code}\n" http://127.0.0.1:8090/v1/models'
'''
rc, out, err = _sshutil.run_remote(sc, timeout=300, host='192.168.50.166')
print(out)
if err.strip():
    print('STDERR:', err[:300])
