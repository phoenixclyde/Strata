import io

P = 'D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv'
s = io.open(P, encoding='utf-8').read()

rows = [
    ('P217', 'MEASUREMENT',
     'gfx906 指令真值裁定：v_dot2_f32_f16 / v_dot4_i32_i8 / v_dot8_i32_i4 / v_mov_b32_dpp 全部可汇编；v_dot4c/dot8c 与 v_mfma 不可',
     'KI 源码里"gfx906 has no integer dot product"是错的；LLVM 文档同名歧义（gfx9-generic 语境）不得照字面读',
     'measurement', 'CONFIRMED', '—', '—', 'P198/P212',
     '166 上实跑 /opt/rocm/llvm/bin/llvm-mc -triple=amdgcn-amd-amdhsa -mcpu=gfx906：'
     'v_dot2_f32_f16 OK / v_dot4_i32_i8 OK / v_dot8_i32_i4 OK / v_mov_b32_dpp OK；'
     'v_dot4c_i32_i8 NO（instruction not supported on this GPU）/ v_mfma_f32_16x16x16_f16 NO。'
     'LLVM AMDGPUUsage 把 dot 指令列在 gfx9-generic 的"gfx906 不可用"清单里，那是 gfx900/902/904 的联合限制。'
     'KI csrc/rocm/dense_gemv_gfx906.cu:600 注释逐字 "gfx906 has no integer dot product, so the MACs run through '
     'the existing __ockl_fdot2 chain" ⇒ 它的 AWQ W4A16 路径全走 fp16 dot2，完全没用 dp4a。'
     '反例：Strata 的 STRATA_DP4A 走 v_dot4_i32_i8，MMQ_KQ=1 实测 +68% prefill（P198）。'
     'skyne98 wiki 用同一方法独立复验，结论一致。',
     '可直接回馈上游/社区：gfx906 上 dp4a 可用且更快；别再照 LLVM 那句做架构判定。'),

    ('P218', 'MEASUREMENT',
     'gfx906 专项优化移植可行性（KI / llama.cpp fork / Strata 三方源码级判定）',
     '补 4 处空白：LDS padding 系统化、DPP 归约、fp16 dot2、fused_gr 的 wave64 通道；预期合计 -5%~-10%',
     'measurement', 'PROPOSED', '—', '—', 'P217',
     '现场：KI=/home/albus/routeK/base/KIntegrated-mobydick@6ccbb03（csrc/gfx906_fa vendored from '
     'cassettesgoboom/gfx906-fa-vllm，源于 skyne98）；llama.cpp 在 166 上只有 third_party/llama.cpp(ggml 3cf0325) '
     '与 mixa3607/llama.cpp-gfx906:v0.5.0 二进制镜像，无 fork 源码 ⇒ 只能搬手法不能搬代码。'
     'Strata 现状（49 个 .cu 全库计数）：__ockl_fdot2 0 处；dpp 2 处（qsa_decode_attn.cu:478 已用 '
     '__builtin_amdgcn_mov_dpp 替代 ds_bpermute）；__shfl_xor 193 处/31 文件；LDS 仅 2 处 padding'
     '（dflash2.cu:107 Sc[32*33]、qsa_select.cu so[][TS_KB+1]）；fused_gr.cu:3101 硬门 prop.warpSize!=32 ⇒ '
     'HC_PERSIST 在 gfx906 上全关（HC 占 16.6%）。已有 wave64 分支：native_mmvq.cu:2343、router_top10.cu:191、'
     'qsa_decode_attn.cu:825（gfx906 && warpSize==64）。'
     '可触及量按 44.98 ms/窗口相位表 = 33 ms(73%)；各项拿 30-50% ⇒ 合计 -5%~-10%。'
     '执行顺序：微基准先行 → router DPP（3 处循环）→ LDS padding → GDN dot2（须过 KL 门，bf16→fp16 会丢指数范围）'
     '→ fused_gr wave64（以周计）。',
     '先做第 0 步微基准（不停服，~30 min），证明 gfx906 上的倍数与 skyne98 的一致，再改引擎。')
]

for r in rows:
    if ('\n' + r[0] + '\t') in ('\n' + s):
        print(r[0], 'exists')
    else:
        s += '\t'.join(r) + '\n'
        print(r[0], 'added')

io.open(P, 'w', encoding='utf-8', newline='\n').write(s)
print('rows now:', len([l for l in s.split('\n') if l.strip()]) - 1)
