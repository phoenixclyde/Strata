import io

P = 'D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv'
s = io.open(P, encoding='utf-8').read()

rows = [
    ('P219', 'MEASUREMENT',
     '上游侦察：KI 本地树落后 1209 commit；三条移植判断被上游数据修正',
     '§3 第 3 项（ALU 换 dot2）降级；杠杆改到字节侧（T1 int8 W8A16 未量化权重）；roofline 先行',
     'measurement', 'CORRECTED', '—', '—', 'P217/P218',
     'GitHub API 实测 2026-10-31：KI 本地 6ccbb03(09-27) vs 上游 3857591d(10-26)，落后 1209 commits，'
     '59 条 gfx906 提交；llama.cpp 上游 0ec4027a(10-31)；Strata 已最新 870aedd9(10-29)。'
     '修正一：KI DEAD-ENDS 有同名实验「dp4a/dot2/dot8 swap in the KQ loop」判 DEAD-END，'
     '理由 "dp4a already inner loop and FULL-RATE (4.44x fp32); B=1 decode is gather-HBM-bound ~2.7x '
     'so ALU swaps cannot surface" ⇒ 对 gather 型 kernel ALU 换指令无效；但我们的 GDN/QSA-score 是 dense GEMV，'
     '机理不同，必须先 roofline 判定而非假设。§5 的「各项 30-50% ⇒ -5~-10%」未区分 gather/dense，作废。'
     '修正二：真杠杆在字节侧。KI T1 probe GO：int8 W8A16 未量化 BF16 权重，lm_head 1.93x、'
     '其他 floor-bound 2.00-2.42x，天花板 dense +10-13% / MoE +14-19%。'
     '我们对应的未量化部分约 14 ms/窗口(31%)：GDN z/out-proj/rec/ab 4.36ms、QSA q/attn/out-proj 4.05ms、'
     'router 3.84ms、head 1.73ms。但 KI 的 T-1（drafter fp16 mass 同手法）最终 NOT PASS，'
     '「earlier +15-18% was a cold-start misread」⇒ probe GO != serving GO。'
     '修正三：同模型(Qwen3.8-Flash-Next/QSA) ISA 事实：fp16 每 32MAC 32 条 v_dot2；bf16 60 条标量 v_fmac_f32；'
     'int8 16 条 v_dot4。QSA kernel pair fp16 26.5ms vs bf16 116.5ms = 3.9x（我们已走 fp16，已吃到）。'
     'tiled indexer fp16 1.39x / bf16 0.42x，须 dtype 门控。int8 KV 在 gfx906 prefill 慢 2.5-2.7x、decode 中性。',
     '改为：roofline 先行(不停服 40min) → T1 同型探针 → indexer tiled 对照 → kv k8v4 prefill 代价核对。'),

    ('P220', 'MEASUREMENT',
     'llama.cpp gfx906 上游状态：#15927 已合并（AMD FP16 dot），#16291 未合并（bpermute→swizzle +20%）',
     'llama.cpp 与 Strata 是平行实现，只共享手法；swizzle 这条路被双向确认',
     'measurement', 'CONFIRMED', '—', '—', 'P217',
     '#15927 MERGED 2025-09-11「CUDA: larger SRAM reads for tile FA, AMD FP16 dot」，SRAM 读 8/16B、'
     'FP32→FP16 转换前置；作者原话「v_dot2_f32_f16 ... available everywhere except for RDNA 1」，'
     '与我们在 166 上用 llvm-mc 的判定一致。'
     '#16291 closed 未合并「hip: substituted bpermute ops with swizzle ops (gfx906)」，实测 +20% 平均——'
     '与我们的 STRATA_GFX906_ATTN_QUERY_SWIZZLE 是同一件事，独立得到同一结论；上游搁置说明 gfx906 只能靠 fork。'
     '#29427 open 把 gfx1012 加进 V_DOT2_F32_F16_AVAILABLE，说明 ggml 有逐架构白名单。'
     'Strata 上游侧顺带发现：#3986 与 #4766 两个 open PR 都在修 dflash2 在 gfx906 的构建（= 我们的 W776），'
     '#3073 SELECT_SIMT=2 是新取值未测，#4781 报 0.1.54 prompt rate 回归且指向 auto expert cache。',
     'llama.cpp 这条线只搬手法不搬代码；swizzle 方向继续。')
]

for r in rows:
    if ('\n' + r[0] + '\t') in ('\n' + s):
        print(r[0], 'exists')
    else:
        s += '\t'.join(r) + '\n'
        print(r[0], 'added')

io.open(P, 'w', encoding='utf-8', newline='\n').write(s)
print('rows now:', len([l for l in s.split('\n') if l.strip()]) - 1)
