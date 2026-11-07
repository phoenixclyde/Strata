# -*- coding: utf-8 -*-
"""W709 审计（机械化证据链）：交付件/记忆里的每个关键数字，必须在原始输出里逐字找到出处。
不判"结论对不对"，只判"这个数字有没有出处" —— 这是可复算的客观检查。
"""
import io, hashlib, os, re

R = r'D:/workbuddy/_z_rk81/'
D = r'D:/strata166/'

def rd(p):
    return io.open(p, encoding='utf-8', errors='replace').read()

SRC = {
    'calib':  rd(R + '_w709_calib_out.json'),
    'pr131':  rd(R + '_pr131.out.txt'),
    'w726':   rd(R + '_w726.out.txt'),
    'w731':   rd(R + '_w731.out.txt'),
    'w732':   rd(R + '_w732.out.txt'),
    'w733':   rd(R + '_w733.out.txt'),
    'w727':   rd(R + '_w727.out.txt'),
    'w736':   rd(R + '_w736.out.txt'),
    'deliv':  rd(D + 'W709_PARAM_OPTIMUM.md'),
    'ho':     rd(D + 'W709_HANDOVER.md'),
    'mem':    rd(r'D:/workbuddy/.workbuddy/memory/2026-10-08.md'),
    'reg':    rd(D + 'params/PARAM_REGISTER.tsv'),
    'gen':    rd(D + 'params/generated/strata-ud-iq4_xs.json'),
    'verify': rd(D + 'params/_verify_w709b.txt'),
}

CHECKS = [
    # (说明, 期望串, 应在哪个源, 该串支撑交付件里的哪句)
    ('P34 效果 A-r1 温TTFT 23.072', 'warm_ttft median=23.072s', 'w733', 'A 臂 23.072/23.074'),
    ('P34 效果 A-r3 温TTFT 23.074', 'warm_ttft median=23.074s', 'w733', 'A 臂 23.072/23.074'),
    ('P34 效果 B-r2 温TTFT 5.861',  'warm_ttft median=5.861s',  'w733', 'B 臂 5.861/5.877'),
    ('P34 效果 B-r4 温TTFT 5.877',  'warm_ttft median=5.877s',  'w733', 'B 臂 5.861/5.877'),
    ('P34 reused=8192 (B臂)',        'warm_cached=[8192, 8192]', 'w733', 'reused=8192'),
    ('P34 A臂 reused=0',             'warm_cached=[0, 0]',      'w733', 'A 臂 cached=0'),
    ('解码确认 A-r1 43.7',           'A-r1 decode  median=43.7',  'pr131', '+9.0% 的 A 臂首轮'),
    ('解码确认 A-r3 42.2',           'A-r3 decode  median=42.2',  'pr131', '+9.0% 的 A 臂次轮'),
    ('解码确认 B 两轮 46.8',          'B-r2 decode  median=46.8',  'pr131', '+9.0% 的 B 臂'),
    ('解码确认 B-r4',                 'B-r4 decode  median=46.8',  'pr131', '+9.0% 的 B 臂'),
    ('解码确认 预填 A 455.8',         'A-r1 prefill median=455.8', 'pr131', '预填 A 455.8/455.3'),
    ('解码确认 预填 A-r3 455.3',      'A-r3 prefill median=455.3', 'pr131', '预填 A 455.8/455.3'),
    ('解码确认 预填 B 455.6',         'B-r2 prefill median=455.6', 'pr131', '预填 B 455.6/456.0'),
    ('解码确认 预填 B-r4 456.0',      'B-r4 prefill median=456.0', 'pr131', '预填 B 455.6/456.0'),
    ('预填A/B A-r1 455.0',            'A-r1 prefill median=455.0', 'w726', 'auto:16384 的 A 455.0/455.1'),
    ('预填A/B A-r3 455.1',            'A-r3 prefill median=455.1', 'w726', 'auto:16384 的 A 455.0/455.1'),
    ('预填A/B B-r2 454.4',            'B-r2 prefill median=454.4', 'w726', 'auto:16384 的 B 454.4/453.7'),
    ('预填A/B B-r4 453.7',            'B-r4 prefill median=453.7', 'w726', 'auto:16384 的 B 454.4/453.7'),
    ('tail 18k A-r1 温5.805',         'warm_ttft median=5.805s',   'w731', 'tail 无效果'),
    ('tail 18k B-r4 温5.805',         'warm_ttft median=5.805s',   'w731', 'tail 无效果'),
    ('tail 18k reused=16384',         'warm_cached=[16384, 16384]', 'w731', '两臂 reused 恒 16384'),
    ('4096 A-r1 温14.742',            'warm_ttft median=14.742s',  'w732', 'every=4096 无效果'),
    ('4096 B-r4 温14.730',            'warm_ttft median=14.730s',  'w732', 'every=4096 无效果'),
    ('calibrate settings',            '"--pcie-frac": "0.20"',     'calib', 'settings 两项'),
    ('calibrate settings min_p',      '"--spec-min-p": "0.70"',    'calib', 'settings 两项'),
    ('sweep pcie 0.20=35.681',        '35.68143171744766',         'calib', 'pcie sweep'),
    ('sweep pcie 0.36=33.708',        '33.70816106180707',         'calib', 'pcie sweep（原 auto）'),
    ('sweep min_p 0.7=36.963',        '36.96323890380894',         'calib', 'min_p sweep'),
    ('sweep workers 21',              '35.90765001262378',         'calib', 'workers 21 最优'),
    ('sweep workers 5',               '29.26383173296754',         'calib', 'workers 5 最差'),
    ('sweep adapt default',           '40.38329315311709',         'calib', 'adapt default 最优'),
    ('confirm 0.36/0.5',              '33.734812745433935',        'calib', '+10.9% 的默认臂'),
    ('confirm 0.20/0.70',             '37.577430056072565',        'calib', '+10.9% 的最优臂'),
    ('复核器 PASS=15',                'PASS=15  FAIL=0',           'verify', 'verify_config 复验'),
    ('register P34',                  'P34',                       'reg', 'P34 新行'),
    ('LIVE config 三旋钮',             '--prompt-cache-every',      'gen', 'config 含 P34'),
]

print('=== 1) 证据链：交付件的数字 -> 原始输出 ===')
ok = bad = 0
for name, needle, src, why in CHECKS:
    hit = needle in SRC[src]
    ok, bad = (ok + 1, bad) if hit else (ok, bad + 1)
    print('  [%s] %-32s in %-7s  <- %s' % ('OK ' if hit else 'MISS', name, src, why))
print('  合计 OK=%d  MISS=%d' % (ok, bad))

print()
print('=== 2) 分辨力区间的可复算性 ===')
def spreads(txt, kind):
    return [float(x) for x in re.findall(r'%s\s+median=[-\d.]+ min=[-\d.]+ max=[-\d.]+ spread=([\d.]+)%%' % kind, txt)]
pre = spreads(SRC['pr131'], 'prefill') + spreads(SRC['w726'], 'prefill')
dec = spreads(SRC['pr131'], 'decode') + spreads(SRC['w726'], 'decode')
print('  预填 spread 读数 =', pre, '=> 区间 %.1f~%.1f%%' % (min(pre), max(pre)), '| 交付件称 1.2~1.7%%')
print('  解码 spread 读数 =', dec, '=> 区间 %.1f~%.1f%%' % (min(dec), max(dec)), '| 交付件称 9.5~15.0%%')

print()
print('=== 3) 无效实验 _w727 有没有被误用 ===')
for tag, txt in [('交付件', SRC['deliv']), ('交接件', SRC['ho']), ('记忆', SRC['mem'])]:
    hits = [l[:110] for l in txt.splitlines() if '_w727' in l]
    print('  %-6s 提及 _w727 的行数 = %d' % (tag, len(hits)))
    for l in hits:
        print('        %s' % l)
print('  _w727 头部自证（证明它跑的是错 bench）：')
hdr = [l for l in SRC['w727'].splitlines() if l.startswith('### 单变量') or l.startswith('# ARM') or l.startswith('===== ARM')]
for l in hdr[:4]:
    print('        %s' % l)

print()
print('=== 4) 落盘件洁净度 ===')
BAN = ['\u21d2', '\u2192', '\u2014', '\u2013', '\u2026', '\u2265', '\u2264', '\u2260', '\u2212', '\u00d7']
for name, p in [('交付件', D + 'W709_PARAM_OPTIMUM.md'), ('交接件', D + 'W709_HANDOVER.md'),
                ('register', D + 'params/PARAM_REGISTER.tsv'), ('生成 config', D + 'params/generated/strata-ud-iq4_xs.json'),
                ('gen_config.py', D + 'params/gen_config.py'), ('verify_config.py', D + 'params/verify_config.py')]:
    b = open(p, 'rb').read(); t = b.decode('utf-8')
    print('  %-14s %7d B md5=%s CR=%d BAN=%s' % (name, len(b), hashlib.md5(b).hexdigest()[:16], b.count(b'\r'),
                                                 {hex(ord(k)): t.count(k) for k in BAN if t.count(k)} or 'CLEAN'))
b = open(r'D:/workbuddy/.workbuddy/memory/2026-10-08.md', 'rb').read(); t = b.decode('utf-8')
print('  %-14s %7d B CR=%d 全件BAN=%s' % ('记忆日志', len(b), b.count(b'\r'), {hex(ord(k)): t.count(k) for k in BAN if t.count(k)}))
seg = t[t.find('## W709'):]
print('  %-14s 本波增量段 BAN=%s' % ('（增量段）', {hex(ord(k)): seg.count(k) for k in BAN if seg.count(k)} or 'CLEAN'))
