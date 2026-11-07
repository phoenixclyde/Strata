# -*- coding: utf-8 -*-
"""修 W-Strata-19 的反引号自伤 + 全文件完整性检查（找其它同类污染）"""
import os, re

p = r'D:\workbuddy_space\2026-10-04-13-25-07\.workbuddy\memory\2026-10-06.md'
t = open(p, encoding='utf-8').read()
before_len = len(t)

MARK = '## [W-Strata-19]'
i = t.find(MARK)
assert i >= 0, 'W-Strata-19 不存在'

CLEAN = '''## [W-Strata-19] **166 已确认下线**（三重判据全部成立），随后按机主指令关闭 Windows

验证时刻取证（`D:\\strata166\\logs\\_shutdown_verify.txt`）：
- **多端口 TCP**：22 / 3000 / 4096 / 8188 / 9090 / 19999 / 8090 **全部 rc=10035（TIMEOUT）**
- **ARP**：arp 全表（9 条有效条目）**无 192.168.50.166 条目**
- **ICMP**：ping 返回 rc=0（**该返回值不可信**），但文本里只有一个回复，且来自 **本机 192.168.50.220**，内容是「无法访问目标主机」
  ⇒ **回复者 != 目标 IP** ⇒ 不算 UP
⇒ **SHUTDOWN_CONFIRMED = YES**

关机前动作：只停了我们自己的 strata166 容器（显存回落到干净的 10,866,688 B）；
**5 个常驻容器（open-webui/portainer/comfyui-cu130/netdata/searxng）刻意未停**，以保留开机自恢复。
166 **无远程唤醒**（无线网卡 + 无 BMC/IPMI），下次使用需现场按电源键。

### [!] 写这条记录时我自己踩的坑（同族第二次）
`python.exe -c "<多行文本>"` 里如果出现**未转义的反引号**，bash 会先做命令替换 ——
本次 `arp -a` 被真的执行、其输出（含 GBK 乱码）被插进了本日志。**已按本节的干净版本整段重写。**
⇒ 定式（与 `routeb-166-channel` 技能的「会话纪律」同一条）：**含反引号 / `$(` / 多行的文本，一律
Write 落 `.py` 文件再执行，禁用 `-c` 内联。** 我明知这条仍踩了，说明"记录过"不等于"防住了"。
'''

t = t[:i] + CLEAN
open(p, 'w', encoding='utf-8').write(t)
print('repaired: %d -> %d chars' % (before_len, len(t)))

# ---- 全文件完整性检查：找同类污染签名 ----
t = open(p, encoding='utf-8').read()
bad = []
for pat, why in [
    ('command not found', 'shell 错误被写入'),
    ('tcp_open_ports', 'JSON 被当命令执行'),
    ('Internet 地址', 'arp 表原始输出泄漏'),
    ('Physical Address', 'arp 表英文输出泄漏'),
    ('数据包: 已发送', 'ping 原始输出泄漏'),
    ('来自 192.168.50.220 的回复', 'ping 原始输出泄漏'),
    ('接口: 192.168', 'ipconfig/arp 输出泄漏'),
]:
    n = t.count(pat)
    if n:
        bad.append((pat, n, why))
print('污染签名扫描:', bad if bad else '（无）')

# 乱码哨兵（GBK 被当 UTF-8 读的典型字节序列）
mojibake = re.findall(r'[ÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß][\u0080-\u00bf]', t)
print('乱码哨兵命中:', len(mojibake))

# 章节标题完整性
heads = re.findall(r'^## \[W-Strata-\d+\].*$', t, re.M)
print('\n章节清单（共 %d 节）:' % len(heads))
for h in heads:
    print('  ', h[:96])
print('\nfinal size =', os.path.getsize(p), 'B')
