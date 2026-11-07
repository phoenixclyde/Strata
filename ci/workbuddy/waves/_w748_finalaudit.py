# -*- coding: utf-8 -*-
"""W709 步31：净化核验审计报告 + 同步 166 + 追加 W709e 记忆 + 终态清单"""
import hashlib, io, os, sys
sys.path.insert(0, r'D:/workbuddy/_z_rk80')
import _sshutil

BANMAP = [('\u21d2', '=>'), ('\u2192', '->'), ('\u2014', '--'), ('\u2013', '-'), ('\u2026', '...'),
          ('\u2265', '>='), ('\u2264', '<='), ('\u2260', '!='), ('\u2212', '-'), ('\u00d7', 'x')]
BANC = [a for a, _ in BANMAP]
D = r'D:/strata166/'

# ---------- 1) 净化审计报告（若首扫就 CLEAN 则不动） ----------
p = D + 'W709_AUDIT.md'
raw = open(p, 'rb').read()
t = raw.decode('utf-8')
hits = {hex(ord(k)): t.count(k) for k in BANC if t.count(k)}
print('[1] 审计报告首扫 BAN =', hits or 'CLEAN')
if hits:
    for a, b in BANMAP:
        t = t.replace(a, b)
nb = t.encode('utf-8')
open(p, 'wb').write(nb)
print('    已净化 -> %d B md5=%s CR=%d' % (len(nb), hashlib.md5(nb).hexdigest(), nb.count(b'\r')))

# ---------- 2) 同步 166 ----------
print()
for lp in [D + 'W709_AUDIT.md', D + 'W709_PARAM_OPTIMUM.md', D + 'W709_HANDOVER.md']:
    ok, size, m, _ = _sshutil.push_b64(lp, '/home/albus/strata166/' + os.path.basename(lp))
    print('[2] push %-26s ok=%s size=%s md5=%s' % (os.path.basename(lp), ok, size, m))

# ---------- 3) 记忆 W709e ----------
SEG = """

## W709e ---- 审计（独立子 agent 通道失败 -> 机械化证据链 + 自查更正）

### 审计方式与**局限**（必须连着看）
- 计划按 `routeb-audit` 规程派**独立只读子 agent**；**3 次全部被中止、零输出**
  （`agent-3e1b74d2b2c5438b` 1m18s / `agent-6564b69165154aae` 1m33s / `agent-92d00641edaf474e` 4m17s，第三次已换独立名字）。
  => **本会话独立子 agent 通道不可用**，改走**机械化证据链审计**（自写核验器），并把独立审计**列为明天待办**。
- 强度上限已写明：核验器能证明"数字有出处 / 落盘件洁净 / 已知措辞问题已改"，
  **不能**证伪"自查者没想到的偏差"（自查与被查是同一方）。

### 机械化证据链（可复算）
- `_w745_audit.py`：**36 条检查 35 OK / 1 MISS**。唯一 MISS 是**核验器选错源文件**
  （`_verify_w709b.txt` 是改 TOOL 分支**之前**的旧捕获件 PASS=14/FAIL=1；PASS=15 在 `_w736.out.txt`）==> 不是数据缺失。
- 分辨力区间**可复算**：预填 8 个 spread => 1.2~1.7%；解码 8 个 => 9.5~15.0%，与交付件一致。
- `_w727` 在交付件与记忆里 **0 命中**，未被误用。

### 两处**实质错误**（这是本次审计的真正产出）
1. **交接件把 `_w727` 的无效原因写错了**：写的是"驱动跑错了 bench"；读原文发现它头部 `bench=/data/bench_prefix.py`、
   正文 `===== PREFIX ARM A-r1`，**是一轮完整有效运行**；真正的问题是 **prompt 只有 6,833 token（短于 chunk 8192）=> 测试域无效**。已改。
   **教训**：我曾读过该文件**被中断时的旧内容**，后来同文件名被完整结果**覆盖**，我拿旧印象下了结论
   => **引用一个文件前必须重读它当前的字节**，不能凭"我上次看过它"。
2. **交付件把"两种测量实现"说成"两个互相独立的方法"**（含 2.4 标题"本机独立复核"、采纳规则"两方法独立同向"）：
   上游 calibrate 与本机 A/B **同机、同引擎、同一时间窗**，只是换了测量实现 => **不是独立复现**。已改为"交叉印证，非独立复现"（4 处）。
3. 附带补标证据等级：「chunk 对齐」= **与观测一致的机制解释，尚未被独立证实**；`0.7 GB` = **推算**（未实测 RAM 曲线）；
   P34 的**适用区间**（只在 ~10,000 token 实测；`>16,384` 未测；`<8,192` 无效）。

### 落盘自查出并已修 6 点
register 2 处 BAN / 两工具件 4 处 BAN / 记忆增量段 13 处 BAN / 本机缺 evidence 副本 /
**交接件 §7 又漏 BAN（描述禁用字符时写字面量）** / **净化器把被引用的禁用字符洗成读不通的 ASCII**（改用 U+XXXX 记法重写）。
- 修复自证判据自纠：首版「反向 undo 逐字节等于原文」在 U+002D 上**映射不唯一** => 必然失败（**判据缺陷，非文件问题**）；
  换成"逐行对齐 + 改动行必原含禁用码位 + new==map(old)"三条后全部 SELF_PROVE_OK。

### 终态
- 交付件 `W709_PARAM_OPTIMUM.md` md5 见下（更正后）；交接件、审计报告均已同步 166。
- **明天首件事**：重跑独立对抗性审计（通道恢复后），重点核"chunk 对齐机制"与"交叉印证 vs 独立复现"。
"""
seg_b = SEG.encode('utf-8')
assert seg_b.count(b'\r') == 0
tt = seg_b.decode('utf-8')
assert not any(c in tt for c in BANC), 'SEG_BAN: %s' % [hex(ord(c)) for c in BANC if c in tt]
MEM = r'D:/workbuddy/.workbuddy/memory/2026-10-08.md'
with open(MEM, 'ab') as f:
    f.write(seg_b)
print()
print('[3] 记忆 %d B CR=%d has W709e=%s' % (os.path.getsize(MEM), open(MEM, 'rb').read().count(b'\r'), 'W709e' in io.open(MEM, encoding='utf-8').read()))

# ---------- 4) 终态清单 ----------
print()
print('[4] 终态清单（本机）')
for f in ['W709_PARAM_OPTIMUM.md', 'W709_HANDOVER.md', 'W709_AUDIT.md',
          'params/PARAM_REGISTER.tsv', 'params/generated/strata-ud-iq4_xs.json',
          'params/gen_config.py', 'params/verify_config.py', 'params/evidence/w709_calib_out.json']:
    q = D + f
    if not os.path.isfile(q):
        print('   %-46s ABSENT' % f); continue
    b = open(q, 'rb').read(); x = b.decode('utf-8', 'replace')
    print('   %-46s %8d B md5=%s CR=%d BAN=%s' % (f, len(b), hashlib.md5(b).hexdigest()[:16], b.count(b'\r'),
                                                 {hex(ord(k)): x.count(k) for k in BANC if x.count(k)} or 'CLEAN'))

sc = r'''
echo "[5] 166 侧终态"
docker ps --format '{{.Names}}|{{.Status}}' | grep strata166-402
docker exec strata166-402 bash -lc 'curl -s -m 8 -o /dev/null -w "http=%{http_code}\n" http://127.0.0.1:8090/v1/models'
md5sum /home/albus/strata166/data/strata-ud-iq4_xs.json /home/albus/strata166/params/PARAM_REGISTER.tsv
ls -la /home/albus/strata166/W709_*.md | awk '{print $5, $9}'
pgrep -af 'calibrate|run_calib|w709' | head -3 || echo "(无残留进程)"
docker ps -a --format '{{.Names}}' | grep -i calib || echo "(无临时容器)"
'''
rc, out, err = _sshutil.run_remote(sc, timeout=300, host='192.168.50.166')
print()
print(out)
if err.strip():
    print('STDERR:', err[:300])
