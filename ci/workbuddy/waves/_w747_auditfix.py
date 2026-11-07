# -*- coding: utf-8 -*-
"""W709 步30：按机械化审计的自查结果，更正交付件与交接件
（每处替换断言 count==1；改后断言 无禁用码位 / CR 不变 / 行数符合预期）
"""
import hashlib, io, os, shutil, time

BAN = ['\u21d2', '\u2192', '\u2014', '\u2013', '\u2026', '\u2265', '\u2264', '\u2260', '\u2212', '\u00d7']
BAKDIR = r'D:/workbuddy/_z_rk81/_bak_w709'
os.makedirs(BAKDIR, exist_ok=True)
TS = time.strftime('%Y%m%d_%H%M%S')

DELIV = r'D:/strata166/W709_PARAM_OPTIMUM.md'
HO = r'D:/strata166/W709_HANDOVER.md'

EDITS = {
    DELIV: [
        # D1 证据强度措辞降级
        ('**两个互相独立的方法同向同量级：+9.0%（本机交错 A/B）与 +10.9%（上游 calibrate 交错 3x3 确认）**',
         '**两种测量实现交叉印证、同向同量级：+9.0%（本机 HTTP 交错 A/B）与 +10.9%（上游 calibrate 交错 3x3）。'
         '注意：同机、同引擎、同期 => 属交叉印证，**不是独立复现**',
         '**替代旧措辞"两个互相独立的方法"**'),
        # D2 采纳规则第 3 条
        ('3. **两方法独立同向**：取上游 calibrate 与本机 A/B 的**交集**（本轮 4 项采纳 / 3 项否决都满足）；',
         '3. **两种测量实现交叉印证**：取上游 calibrate 与本机 A/B 的**交集**（本轮 4 项采纳 / 3 项否决都满足）。\n'
         '   **这不是"独立复现"**：同一台机、同一个引擎、同一时间窗，只换了测量实现；',
         ''),
        # D3 小节标题
        ('### 2.4 本机独立复核（防单一来源）',
         '### 2.4 本机交叉复核（另一种测量实现；**非独立复现**）',
         ''),
        # D4 小结句
        ('两个方法独立、同向、同量级；**且预填不动**',
         '两种测量实现同向、同量级；**且预填不动**（同机同引擎同期 => 交叉印证，非独立复现）',
         ''),
        # D5 机制条目的证据等级
        ('   把 interval 降到 **4096 反而一点不复用**（`reused=0`，因为 4096 不与 8192 对齐）；',
         '   把 interval 降到 **4096 反而一点不复用**（`reused=0`，因为 4096 不与 8192 对齐）。\n'
         '   **[!] 证据等级**：本条只有"4096 无效 + 8192 有效 + 18k 复用 16384"三处观测支撑，'
         '属**与观测一致的机制解释，尚未被独立证实**（没有第二类独立实验，如改变 chunk 大小来看对齐点是否随之移动）；',
         ''),
        # D6 适用区间
        ('> 盲区在 **8192 ~ 16384 这一段**，`8192` 正是补它。\n\n### 3.3 资源代价',
         '> 盲区在 **8192 ~ 16384 这一段**，`8192` 正是补它。\n'
         '>\n'
         '> **[!] 适用区间（未测部分）**：本项只在 **~10,000 token** 一档上实测。'
         '`> 16,384` token 的 prompt 默认已有 checkpoint、`8192` 只是多一个，**是否有增量收益未测**；'
         '`< 8192` token 无效（无 chunk 边界）。\n\n### 3.3 资源代价',
         ''),
        # D7 推算标注
        ('`checkpoint` 计入 `--prompt-cache N`（默认 6）上限，help 记 **~118 MB/个** => 上限约 **0.7 GB RAM**。',
         '`checkpoint` 计入 `--prompt-cache N`（默认 6）上限，help 记 **~118 MB/个** => **推算**上限约 **0.7 GB RAM**'
         '（**这是推算值，未实测 RAM 曲线**）。',
         ''),
    ],
    HO: [
        # H1 更正 _w727 的无效原因（我原先写错了）
        ('**已知的无效产物（不要引用）**：`D:/workbuddy/_z_rk81/_w727.out.txt`\n'
         '---- 那一轮 `--prompt-cache-tail` 的 A/B 因驱动把 bench 路径硬编码成 `bench_ver.py` 而**跑错了探针**；\n'
         '正确结果在 `_w731.out.txt`。',
         '**测试域无效、不要当结论引用**：`D:/workbuddy/_z_rk81/_w727.out.txt`\n'
         '---- 它其实是**一轮完整有效运行**的 `--prompt-cache-tail` A/B（4 臂全跑完、数据自洽），'
         '但用的 prompt 只有 **6,833 token（短于一个 chunk 8192）** => 该 flag 的机制前提不成立，**是测试域无效**。\n'
         '正确结果（18,083-token prompt）在 `_w731.out.txt`。\n'
         '（**更正记录**：本件初版把原因写成"驱动跑错了 bench"----那是我**误读了输出**；'
         '原文头部是 `bench=/data/bench_prefix.py`、正文是 `===== PREFIX ARM A-r1`，探针没错。）',
         ''),
        # H2 净化导致引用失真 -> 改码位记法
        ('含 2 个禁用码位（`3x3` 的 `x`、P32 行的 `=>`）',
         '含 2 个禁用码位（`3x3` 里的乘号 U+00D7、P32 行的 U+21D2）',
         ''),
        # H3
        ('含 `=>`x1 + `--`x12',
         '含 U+21D2 x1 + U+2014 x12',
         ''),
        # H4
        ('（可能来自 `-`/`-`）',
         '（U+002D 可能来自 U+2013 或 U+2212）',
         ''),
    ],
}

for path, edits in EDITS.items():
    raw = open(path, 'rb').read()
    shutil.copy2(path, os.path.join(BAKDIR, os.path.basename(path) + '.auditfix_%s' % TS))
    t = raw.decode('utf-8')
    n = 0
    for old, new, note in edits:
        c = t.count(old)
        assert c == 1, 'HIT!=1 (%d) in %s for: %r' % (c, os.path.basename(path), old[:70])
        t = t.replace(old, new, 1)
        n += 1
    nb = t.encode('utf-8')
    assert nb.count(b'\r') == raw.count(b'\r'), 'CR_DRIFT'
    assert not any(ch in t for ch in BAN), 'BAN_INTRUDED %s' % [hex(ord(c)) for c in BAN if c in t]
    open(path, 'wb').write(nb)
    print('%-26s 替换 %d 处  %d -> %d B  md5=%s  CR=%d  BAN=CLEAN' % (
        os.path.basename(path), n, len(raw), len(nb), hashlib.md5(nb).hexdigest(), nb.count(b'\r')))
