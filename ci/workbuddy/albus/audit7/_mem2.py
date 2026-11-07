import hashlib, io, json, os, subprocess, sys

TOOLS = r'D:/workbuddy_space/strata_ws/deploy/tools'
MEM = r'D:/workbuddy_space/strata_ws/.workbuddy/memory/MEMORY.md'
SKILL = r'C:/Users/clyde/.workbuddy/skills/routek-memory-slim/SKILL.md'

s = io.open(MEM, encoding='utf-8').read()
ops = []

def add(old, new):
    n = s.count(old)
    assert n == 1, (n, old[:50])
    ops.append({'kind': 'substr', 'old': old, 'new': new})

# 新增：计时行口径（尽量短）
add('- **自比须同形状**；比 `ms/step`（`tok/s` 受净出污染）；不可复现先排冷热',
    '- **自比须同形状**；比 `ms/step`；不可复现先排冷热；**计时行含adapt+join**(曾10.69ms被漏)')

# 新增：占用率口径（短版）
add('- **草稿深度自适应**，kShape编译期常量非旋钮(W8)；同卡 L2=8MB/HBM~805',
    '- **草稿深度自适应**，kShape编译期常量非旋钮(W8)；同卡 L2=8MB/HBM~805\n'
    '- **占用率**=块/CUx线程/64/40(wave64);HC 41块=6.8%=>只加块数,TILEV无效(P96/W789)')

# 新增：governor 口径（短版）
add('- **prefill热态=GPU+CPU双满(地板,file tier 0)**;单轮decode占S43/M10/L0.5%,**多轮复用后decode占大头**',
    '- **prefill热态=GPU+CPU双满(地板,file tier 0)**;单轮decode占S43/M10/L0.5%,**多轮后decode占大头**;基线测于performance,现schedutil(P97)')

# 压缩四处以腾出空间
add('无--resident-experts(W785去掉;三档decode+10~12%,prompt不减;spec仍6)',
    '无--resident-experts(W785;decode+10~12%)')
add('env：**STRATA_HC_Q8=1**(0.1.48;gfx906默认关;+0.6%,槽9732->9901)',
    'env：**STRATA_HC_Q8=1**(gfx906默认关;+0.6%,槽9732->9901)')
add('- **verify_config.py 只判配置面** => 运行期另取引擎 /proc（W764）',
    '- **verify_config.py 判配置面** => 运行期取引擎 /proc(W764)')
add('- **166 PCIe**：有效 **Gen3 x16**；pcie_bw 读~1s 须独线程',
    '- **166 PCIe**：Gen3 x16；pcie_bw 读~1s 须独线程')
add('P54=IO_PF_STAGE(判据blob读0);B8无增益', 'P54=IO_PF_STAGE;B8无增益')

md5 = hashlib.md5(open(SKILL, 'rb').read()).hexdigest()
pf = os.path.join(TOOLS, 'plan_audit7b.json')
io.open(pf, 'w', encoding='utf-8', newline='\n').write(
    json.dumps({'skill_md5': md5, 'ops': ops}, ensure_ascii=False, indent=1))
print('ops=%d' % len(ops))

r = subprocess.run([sys.executable, os.path.join(TOOLS, 'mem_slim.py'), 'apply', pf],
                   cwd=TOOLS, capture_output=True, text=True)
print('rc=%d' % r.returncode)
print((r.stdout or '')[-900:])
print((r.stderr or '')[-500:])
