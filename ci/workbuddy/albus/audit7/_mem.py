import hashlib, io, json, os, subprocess, sys

TOOLS = r'D:/workbuddy_space/strata_ws/deploy/tools'
MEM = r'D:/workbuddy_space/strata_ws/.workbuddy/memory/MEMORY.md'
SKILL = r'C:/Users/clyde/.workbuddy/skills/routek-memory-slim/SKILL.md'

s = io.open(MEM, encoding='utf-8').read()

ops = []

def add(old, new):
    n = s.count(old)
    assert n == 1, (n, old[:60])
    ops.append({'kind': 'substr', 'old': old, 'new': new})

# 1) 计时行口径（合并进已有纪律行，省字符）
add('- **自比须同形状**；比 `ms/step`（`tok/s` 受净出污染）；不可复现先排冷热',
    '- **自比须同形状**；比 `ms/step`；不可复现先排冷热；**计时行=verify+commit+draft+adapt+join**(adapt曾10.69ms被漏)')

# 2) 占用率口径（新行）
add('- **草稿深度自适应**，kShape编译期常量非旋钮(W8)；同卡 L2=8MB/HBM~805',
    '- **草稿深度自适应**，kShape编译期常量非旋钮(W8)；同卡 L2=8MB/HBM~805\n'
    '- **占用率**=块/CU×线程/64/40(wave64/60CU)；HC 41块=6.8% => 只加块数,TILEV无用(P96/W789)')

# 3) governor 口径（挂在 prefill 行尾）
add('- **prefill热态=GPU+CPU双满(地板,file tier 0)**;单轮decode占S43/M10/L0.5%,**多轮复用后decode占大头**',
    '- **prefill热态=GPU+CPU双满(地板,file tier 0)**;单轮decode占S43/M10/L0.5%,**多轮后decode占大头**;基线均测于gov=performance,现schedutil(P97)')

# 4) 压缩省字符
add('无--resident-experts(W785去掉;三档decode+10~12%,prompt不减;spec仍6)',
    '无--resident-experts(W785;decode+10~12%)')
add('- **改答案判据**：按 index 跨臂对齐（spread 才真判据，W739）',
    '- **改答案判据**：按 index 跨臂对齐(W739)')

md5 = hashlib.md5(open(SKILL, 'rb').read()).hexdigest()
plan = {'skill_md5': md5, 'ops': ops}
pf = os.path.join(TOOLS, 'plan_audit7.json')
io.open(pf, 'w', encoding='utf-8', newline='\n').write(json.dumps(plan, ensure_ascii=False, indent=1))
print('plan written with %d ops' % len(ops))

py = sys.executable
for step in ('plan', 'apply'):
    r = subprocess.run([py, os.path.join(TOOLS, 'mem_slim.py'), step, pf],
                       cwd=TOOLS, capture_output=True, text=True)
    print('=== %s rc=%d' % (step, r.returncode))
    print((r.stdout or '')[-900:])
    print((r.stderr or '')[-600:])
