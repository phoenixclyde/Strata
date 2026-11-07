# -*- coding: utf-8 -*-
"""追加 W709d（落盘确认 + 修复 + 交接件）到今日日志

注：描述禁用码位时**不得写字面量**（引文不是豁免区）=> 一律用 U+XXXX 记法。
"""
import io, os
P = r'D:/workbuddy/.workbuddy/memory/2026-10-08.md'
SEG = """

## W709d ---- 收口：落盘确认 -> 自查出 4 点并修复 -> 交接件

### 落盘确认（统一量一遍，不靠印象）
- 交付件 `W709_PARAM_OPTIMUM.md` = 13,705 B / `550be73648e89d03990a36944dff9343` / CR=0 / BAN CLEAN。
- register 两机同 md5；LIVE config `d2b10f0c4e8293ba010614c7acc70bea`；启动行三旋钮齐；
  `verify_config.py` = PASS 15 / FAIL 0 / SKIP 1；166 无临时容器、无残留进程、VRAM 33.96 GB、磁盘 73%。

### [!] 这一步真的查出 4 点（不查就会带着缺陷过夜）
1. `PARAM_REGISTER.tsv` 含 **2 个禁用码位**（`3x3` 里的那个乘号被写成 U+00D7；P32 行一个 U+21D2）=> 已清（改动 2 行）。
2. `gen_config.py`(1 行) / `verify_config.py`(3 行) 含 U+2014 长破折号 => 已清。
3. 记忆日志 `2026-10-08.md` 的**本波增量段**（`## W709a` 起）含 U+21D2 x1 + U+2014 x12 => 已清（改动 7 行）；
   **更早段落的存量命中单独报出、非本波缺陷**（按 T96「判 BAN 要分增量区与存量区」）。
4. 本机 `params/evidence/` **缺** `w709_calib_out.json`（此前只推到了 166，本机没留副本）=> 已补。

### [!] 修复自证判据的一次自纠（判据有缺陷，不是文件有问题）
- 首版自证写「**反向 undo 必须逐字节等于原文**」，但连字符的反向映射**不唯一**
  （U+002D 可能来自 U+2013 或 U+2212），undo 会把**所有连字符**都变成减号 => 断言必然失败。
- 换成三条逐行可核的判据：① 改后无禁用码位；② **行数不变**且 `equal` 块逐行字节相同；
  ③ `replace` 块里每对 (old,new) 满足 `new == 对 old 施加同一张替换表`，且 **old 行必含至少一个禁用码位**
  （=> 排除「无故改动」）。四个文件全部 SELF_PROVE_OK。
- 教训：**可逆性自证用的映射必须是一一映射**；多对一的替换表不能拿「undo 回原文」当判据。

### 交接件（明天续接用）
- `D:/strata166/W709_HANDOVER.md`（9,666 B / `d6efd0bc17f053b5be72d6d6c9574535` / CR=0），已同步 166。
  含：① 一页速览 + 终态指纹（明天开工先核）；② 固化机制的唯一合法通道（改 register -> 生成 -> 部署 -> 复验）；
  ③ 三个关键机制发现（chunk 对齐 / tail 冗余 / 盲区 8192~16384）；④ **五项未测项的测量配方**；
  ⑤ 避坑清单 5 条；⑥ 复现与回滚；⑦ 产物索引 + 已知无效产物标注。
- register 指纹更新为 `a91b677ea13905cb36ef56fa6224c36d`（修复后）；166 侧复验：35 行 / 16-12-7 / BAN CLEAN。
"""
b = SEG.encode('utf-8')
assert b.count(b'\r') == 0
BAN = ['\u21d2', '\u2192', '\u2014', '\u2013', '\u2026', '\u2265', '\u2264', '\u2260', '\u2212', '\u00d7']
tt = b.decode('utf-8')
assert not any(c in tt for c in BAN), 'SEG_HAS_BAN: %s' % [hex(ord(c)) for c in BAN if c in tt]
with open(P, 'ab') as f:
    f.write(b)
t = io.open(P, encoding='utf-8').read()
print('memory %d B CR=%d  has W709d=%s' % (os.path.getsize(P), open(P, 'rb').read().count(b'\r'), 'W709d' in t))
