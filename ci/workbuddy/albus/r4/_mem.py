import hashlib, io, json, os, subprocess, sys

TOOLS = r'D:/workbuddy_space/strata_ws/deploy/tools'
MEM = r'D:/workbuddy_space/strata_ws/.workbuddy/memory/MEMORY.md'
SKILL = r'C:/Users/clyde/.workbuddy/skills/routek-memory-slim/SKILL.md'

s = io.open(MEM, encoding='utf-8').read()
ops = []


def add(old, new):
    assert s.count(old) == 1, (s.count(old), old[:56])
    ops.append({'kind': 'substr', 'old': old, 'new': new})


# 新增一条（路由 / GR_SPLIT）
add('- **草稿深度自适应**，kShape编译期常量非旋钮(W8)；同卡 L2=8MB/HBM~805',
    '- **草稿深度自适应**，kShape编译期常量非旋钮(W8)；同卡 L2=8MB/HBM~805\n'
    '- **路由**:k10走native_router(无fp64),router_top10旁路;GR_SPLIT仅bf16净负(P101/102)')

# 压缩
add('- **重启丢前2请求**(专家冷17.4->10.3);A/B同会话交错(P98)',
    '- **重启丢前2请求**(专家冷);A/B同会话交错(P98)')
add('- **HC**:down不敏感int8/bf16;up余量14%(2.96);HC_Q8优-3.2%+169槽(P100)',
    '- **HC**:down不敏感int8/bf16;up余量14%;HC_Q8优-3.2%+169槽(P100)')
add('- **dot**：dot4 62,596/dot8 0=>dp4a+解包;换dot8须双方i4(P38)',
    '- **dot**:dot4 62,596/dot8 0=>dp4a;换dot8须双方i4(P38)')
add('- **KV门**(P51)：`STRATA_LOGPOS`须两请求,fresh<=`--short-read`,self=0；W770 6/6=>k8v4无损',
    '- **KV门**(P51):STRATA_LOGPOS须两请求,fresh<=--short-read,self=0；W770 6/6=>k8v4无损')
add('- 源码4树 deploy/tmp/_src/;对账 todo_reconcile.py --strict',
    '- 源码4树 deploy/tmp/_src/;对账 todo_reconcile.py')
add('- **占用率**=块/CUx线程/64/40(wave64);HC 41块6.8%=>只加块数,TILEV无效(P96)',
    '- **占用率**=块/CUx线程/64/40(wave64);HC 41块6.8%=>只加块数(P96)')
add('- **W775delta**：P55/P56不可达;PLE ram -45%(否);P54=IO_PF_STAGE;B8/B7废;drop_caches不重置mmap页',
    '- **W775delta**:P55/P56不可达;PLE ram-45%(否);P54=IO_PF_STAGE;B8/B7废;drop_caches不重置mmap')

md5 = hashlib.md5(open(SKILL, 'rb').read()).hexdigest()
pf = os.path.join(TOOLS, 'plan_w791.json')
io.open(pf, 'w', encoding='utf-8', newline='\n').write(
    json.dumps({'skill_md5': md5, 'ops': ops}, ensure_ascii=False, indent=1))
print('ops=%d' % len(ops))

r = subprocess.run([sys.executable, os.path.join(TOOLS, 'mem_slim.py'), 'apply', pf],
                   cwd=TOOLS, capture_output=True, text=True)
print('rc=%d' % r.returncode)
print((r.stdout or '')[-700:])
print((r.stderr or '')[-300:])
