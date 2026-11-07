import hashlib, io, json, os, subprocess, sys

TOOLS = r'D:/workbuddy_space/strata_ws/deploy/tools'
MEM = r'D:/workbuddy_space/strata_ws/.workbuddy/memory/MEMORY.md'
SKILL = r'C:/Users/clyde/.workbuddy/skills/routek-memory-slim/SKILL.md'

s = io.open(MEM, encoding='utf-8').read()
ops = []


def add(old, new):
    assert s.count(old) == 1, (s.count(old), old[:56])
    ops.append({'kind': 'substr', 'old': old, 'new': new})


# --- 新增两条（尽量短） ---
add('- **草稿深度自适应**，kShape编译期常量非旋钮(W8)；同卡 L2=8MB/HBM~805\n',
    '- **草稿深度自适应**，kShape编译期常量非旋钮(W8)；同卡 L2=8MB/HBM~805\n'
    '- **重启丢前2请求**(冷专家17.4->10.3,偏高3%);A/B必同会话交错(P98)\n'
    '- **HC**:down对int8/bf16不敏感(3.47);up余量14%(2.96);HC_Q8净优-3.2%+169槽(P100)\n')

# --- governor 结论替换（同长度，信息更强） ---
add(';基线测于performance,现schedutil(P97)', ';**gov schedutil快2.3%**(P97)')

# --- 压缩 ---
add('- **KV 门**（P51）：`STRATA_LOGPOS` 须**两请求**、fresh<=`--short-read`；**self=0**。W770 needle 6/6 => `k8v4` 无损失',
    '- **KV门**(P51)：`STRATA_LOGPOS`须两请求,fresh<=`--short-read`,self=0；W770 6/6=>k8v4无损失')
add('- **W775delta**：P55/P56于k8v4不可达;PLE ram -45%(否);P54=IO_PF_STAGE;B8/B7废(W785);drop_caches不重置mmap页',
    '- **W775delta**：P55/P56不可达;PLE ram -45%(否);P54=IO_PF_STAGE;B8/B7废;drop_caches不重置mmap页')
add('- **dot**：dot4 62,596/dot8 0 => dp4a+解包；换 dot8 须双方 i4（P38）',
    '- **dot**：dot4 62,596/dot8 0=>dp4a+解包;换dot8须双方i4(P38)')
add('- **改答案判据**：按 index 跨臂对齐（spread 才真判据，W739）', '- **改答案判据**：按index跨臂对齐(W739)')
add('- **自比须同形状**；比 `ms/step`；不可复现先排冷热；**计时行含adapt+join**(曾10.69ms被漏)',
    '- **自比同形状**;比`ms/step`;不可复现先排冷热;**计时行含adapt+join**(曾10.69ms漏)')
add('- **166 PCIe**：Gen3 x16；pcie_bw 读~1s 须独线程', '- **166 PCIe**：Gen3x16;pcie_bw读~1s须独线程')
add('- **占用率**=块/CUx线程/64/40(wave64);HC 41块=6.8%=>只加块数,TILEV无效(P96/W789)',
    '- **占用率**=块/CUx线程/64/40(wave64);HC 41块6.8%=>只加块数,TILEV无效(P96)')
add('- **verify_config.py 判配置面** => 运行期取引擎 /proc(W764)',
    '- **verify_config只判配置面**=>运行期取引擎/proc(W764)')
add('- 改裁定后按 ID 全文 grep 同步(W752)', '- 改裁定按ID全文grep同步(W752)')
add('- 多文件同走 stdout 须补尾换行', '- 多文件同走stdout须补尾换行')

md5 = hashlib.md5(open(SKILL, 'rb').read()).hexdigest()
pf = os.path.join(TOOLS, 'plan_w790.json')
io.open(pf, 'w', encoding='utf-8', newline='\n').write(
    json.dumps({'skill_md5': md5, 'ops': ops}, ensure_ascii=False, indent=1))
print('ops=%d' % len(ops))

r = subprocess.run([sys.executable, os.path.join(TOOLS, 'mem_slim.py'), 'apply', pf],
                   cwd=TOOLS, capture_output=True, text=True)
print('rc=%d' % r.returncode)
print((r.stdout or '')[-800:])
print((r.stderr or '')[-400:])
