import csv, shutil

P = 'deploy/params/PARAM_REGISTER.tsv'
shutil.copyfile(P, 'albus/w824/PARAM_REGISTER.bak.tsv')
rows = list(csv.reader(open(P, encoding='utf-8'), delimiter='\t'))
hdr, body = rows[0], rows[1:]

ADD = {
    'P152': ['P152', 'VERSION', 'engine 0.1.49.2 -> 0.1.53（tag v0.2.7.1）', '0.1.53', 'version/upgrade',
             'ADOPTED', '服务层自建（上游不发 gfx906 包）', '—', 'P146', 
             'W824：上游对 x86 Qwen 引擎在 0.2.7->0.2.7.1 只改 4 个编译相关文件 + CMakeLists（其余 26 个是 dsv41/metal，'
             '我们 -DSTRATA_BUILD_DSV41=OFF 且 Linux 不编 metal）。codeload 限速到 10-21 KB/s，改用文件级移植：'
             'tar 管道复制 0.2.7 源码树（258 MB/7973 文件/1.9 s）+ 覆盖 5 个文件 + 重打 3 处补丁（A/B/C）+ W794 已在树中。'
             '构建 164/164 rc=0，38,237,344 B，--version = strata 0.1.53；strings 有 rocBLAS tuning enabled / MMQ_KQ / '
             'PLE_AUTO_RAM / EXPERT_V2K，gfx906 代码对象 140，--help 139 flag（与 0.1.49.2 零差异）。'
             'A/B/A2 三臂：prefill 1453/2498/4568 -> A 3.73/5.27/8.26、B53 4.07/5.31/8.53、A2 3.90/5.26/8.27；'
             '同二进制漂移带 4.6%（A vs A2），B53 的 +0.8~4.4% 在带内 ⇒ 无可测差异；启动 199/240/231 s 无差异。',
             '采纳（机主要求升到最新；无回归证据，含 #3602/#1503 正确性修复）。回滚：exe 改回 /src/build-906/strata。'],
    'P153': ['P153', 'ENV', 'STRATA_EXPERT_V2K=1（Q4_K 的 V2K 解码内核）', '0（默认关）', 'decode-kernel',
             'REJECTED', '需 gu_type=12/d_type=7/n_embd=2560/n_ff=640（我们正好匹配）', '—', 'P152',
             'W824：机制完全对口——iq_kernels.cu:5103 的启用条件是 Q4_K gate/up + Q5_1/Q8_0 down + 2560x640，'
             '而 gfx906 落在 `#if defined(__HIPCC__) && !defined(STRATA_HIP_GFX906)` 的 else 分支（默认 false），必须显式 =1；'
             '上游称与旧内核逐位相同（QUANTS.md:"CUDA layout; STRATA_EXPERT_V2K=1 bitwise"）。'
             '首测 T1 45.0 vs 基线 N0 41.8（+7.7%），但配对重跑 N0b 46.9 vs T1b 46.9 = **0.0%**，'
             '且 prefill 4563 tok 全程 7029-7060 ms（差 0.4%）⇒ 初次的 +7.7% 是容器漂移（同配置 N0->N0b 就 +12%）。',
             '不采纳。零质量风险，留给 ABBA 交错复测。'],
    'P154': ['P154', 'ARG', '--spec-min-p 0.50（上游 setup 值；我们是 0.70）', '0.70', 'decode/spec',
             'REJECTED', '—', '—', 'P152',
             'W824：--spec-min-p 的语义是"草稿层要有多确定才把验证窗口再延长一次"（上游 setup 写 0.5）。'
             'T2b 解码中位 40.1 vs 同窗口基线 N0b 46.9 = **−14.5%**；prefill 7037 vs 7029 ms（无变化）。'
             '⇒ 在这台机上"更积极地延长窗口"是纯亏（每个额外 token 都要付 30.7% 覆盖率下的专家 miss）。',
             '保持 0.70。下一轮沿反方向试 0.85。'],
    'P155': ['P155', 'PHASE', '`ple` 相位在 UD-Q4_K_XL 上的占比（对 P138/P141 重新定级）', '0.5-0.9%', 'phase',
             'CORRECTION', '—', '—', 'P138/P141',
             'W824：同一台机、同一张 26.8 GiB 表、4563 token，0.1.53 的相位表显示 ple 只有 **34-42 ms / 0.5-0.9%**，'
             '而 W810 在 UD-IQ4_XS 上是 **12.9-16.7%**（约 250 ms/1k）。五臂一致（N0/T1/N0b/T1b/T2b）。'
             '机理（推测未单验）：表整张留在页缓存（Cached 52 GB），ple 不再等盘；W810 当时 ComfyUI 占 52 GB、'
             '表被竞技场 55.43 GiB 缓冲流冲掉才有等盘。边界：host 侧 "chunk setup (PLE rows)" 仍 80-138 ms，'
             '且页缓存被挤掉就会退回 W810 形态 ⇒ 是"当前内存状态的结果"，不是结构性消失。'
             '新的时间构成（4563 tok）：gate/up 21.8% + gemm down 14.1% + attn 15.5% + gdn 11.4% + qsa proj 8.7% + hc read 8.3%。',
             'P138/P139/P140/P142 在新权重下降为低优先；主战场是 gate/up+down（36%）与 attn（15.5%）。'],
}

out, seen = [], set()
for r in body:
    if r[0] == 'P150':
        r[10] = r[10].rstrip() + '\n【W824 追加】按机主要求**删除 aliases**，只保留新名。' \
                 '兼容性已核：/v1/chat/completions 不校验 model 名（只有 /v1/load、/v1/unload、/props 会 404）' \
                 '⇒ 旧名客户端聊天不受影响，走 /props 的工具要改填新名。'
    if r[0] in ADD:
        seen.add(r[0])
        out.append(ADD[r[0]])
    else:
        out.append(r)
for k, v in ADD.items():
    if k not in seen:
        out.append(v)

with open(P, 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f, delimiter='\t', lineterminator='\n')
    w.writerow(hdr); w.writerows(out)
print('rows', len(out), 'bad_cols', [r[0] for r in out if len(r) != 11])
