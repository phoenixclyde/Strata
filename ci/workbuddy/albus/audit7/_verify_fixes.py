import io, os, re

BASE = 'D:/workbuddy_space/strata_ws/'
D = BASE + 'deploy/'

checks = []

def chk(name, path, must, forbid=None):
    p = os.path.join(D, path) if not os.path.isabs(path) else path
    if not os.path.exists(p):
        checks.append((name, 'MISSING FILE', path))
        return
    s = io.open(p, encoding='utf-8').read()
    ok = all(m in s for m in must)
    bad = [f for f in (forbid or []) if f in s]
    checks.append((name, 'PASS' if ok and not bad else 'FAIL',
                   'missing=%s forbid_hit=%s' % ([m[:28] for m in must if m not in s], bad[:2])))

# 1 AUDIT6 撤回
chk('1 AUDIT6 P2-7 撤回标记', 'AUDIT6_W776_W785.md',
    ['AUDIT7 P1-1` 撤回', 'adapt wait 10.69 join 0.61'])

# 2 W786 三处
chk('2a W786 L 列改 3.10', 'W786_TARGET_CORRECTION.md', ['| 3.10 (7.8%) |'])
chk('2b W786 自校验改准确', 'W786_TARGET_CORRECTION.md', ['AUDIT7 P2-2 更正', '46.11 / 47.34 / 39.90', '已由 46.35 改为 **46.13**'])
chk('2c W786 旧表指控改口径混用', 'W786_TARGET_CORRECTION.md',
    ['口径混用', '不是因为它算错了'])

# 3 W788 四处
chk('3a W788 占用率 6.8%', 'W788_HC_ATTRIBUTION.md', ['6.8%', 'Wavefront Size: 64'])
chk('3b W788 根因拆分', 'W788_HC_ATTRIBUTION.md', ['shared 在这里不是约束'])
chk('3c W788 路径 A 判无效', 'W788_HC_ATTRIBUTION.md', ['已判无效，不要做', 'AUDIT7 P1-3'])
chk('3d W788 小计与地板', 'W788_HC_ATTRIBUTION.md', ['列相加 7.47'])

# 4 W787 条件
chk('4 W787 端到端条件', 'W787_R1_FAILURE_REVIEW.md', ['AUDIT7 P2-4', '7.9% / 4.8% / 9.5%'])

# 5 W776 队列
chk('5a W776 R5 改加块数', 'W776_TUNING_MASTER_PLAN.md', ['R5（第一）', '只做「加块数」'])
chk('5b W776 governor 口径', 'W776_TUNING_MASTER_PLAN.md', ['AUDIT7 P1-4` / `P97'])
chk('5c W776 队列去重', 'W776_TUNING_MASTER_PLAN.md', [], forbid=['**R3** 量化+dense GEMV（13.3%）· **R4** 路由 fp64（8.1%）\n- **R2**'])

# 6 W785 banner
chk('6 W785 第三类白跑', 'W785_MASTER_QUEUE.md', ['第三类白跑', 'W789_R5_TILEV_VERDICT'])

# 7 W789 新件
chk('7 W789 存在且完整', 'W789_R5_TILEV_VERDICT.md', ['源码级无效', '加块数', 'P2-6'])

# 8 register
reg = io.open(D + 'params/PARAM_REGISTER.tsv', encoding='utf-8-sig').read().splitlines()
row = {}
for ln in reg[1:]:
    f = ln.split('\t')
    row[f[0]] = f
chk('8a P96 -> REJECTED', 'params/PARAM_REGISTER.tsv', ['REJECTED（源码级反证'])
chk('8b P97 存在', 'params/PARAM_REGISTER.tsv', ['P97\tdecode\t基线 governor 口径'])
chk('8c P91 补更正', 'params/PARAM_REGISTER.tsv', ['AUDIT7 P2-1/P2-2 更正'])
chk('8d P95 补更正', 'params/PARAM_REGISTER.tsv', ['AUDIT7 更正 2026-10-25 06:3x'])

# 9 MEMORY 三条
mem = io.open(BASE + '.workbuddy/memory/MEMORY.md', encoding='utf-8').read()
for nm, txt in (('9a 计时行', '计时行含adapt+join'),
                ('9b 占用率', '占用率**=块/CUx线程/64/40'),
                ('9c governor', '基线测于performance,现schedutil')):
    checks.append((nm, 'PASS' if txt in mem else 'FAIL', 'chars=%d' % len(mem)))

print('%-26s %-6s %s' % ('整改项', '结果', '备注'))
print('-' * 92)
fails = 0
for n, st, note in checks:
    if st != 'PASS':
        fails += 1
    print('%-26s %-6s %s' % (n, st, note))
print('-' * 92)
print('total=%d  fail=%d' % (len(checks), fails))
