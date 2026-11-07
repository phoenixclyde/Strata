import io

P = 'D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv'
s = io.open(P, encoding='utf-8').read()

rows = [
    ('P221', 'MEASUREMENT',
     'Strata 自身可扩展到 gfx906 的清单：gfx906 无架构谓词，arch_defaults 直接 return 空表；缺口分 A/B/C 三类',
     'A 类（纯实现缺口）4 项开关 + HC_UPMIX + GDN_CHUNKED 算法 + CKPT/PARK 族；B 类硬件不符不做；C 类路径不适用不做',
     'measurement', 'PROPOSED', '—', '—', 'P207/P219',
     'src/core/arch_defaults.cpp:25-93：先 if(gfx12){RDNA4 表 9 项}，再 if(!gfx1151) return t —— gfx906 在此 return 空表。'
     '全库只有 4 个架构谓词（gfx12 16 / gfx11_wmma 9 / gfx1151 5 / gfx12_wmma 3），无 gfx906 谓词。'
     'A 类（kernel 侧无架构门控，只是进不了表，全部纯 getenv 读取）：'
     'STRATA_ATTN_LANECELL（qsa_decode_attn.cu:916/1161，源码逐字 bit-identical scores, no shuffle reductions）；'
     'STRATA_TSUM（fused_gr.cu:2259 + iq_kernels.cu:6270，逐字 bitwise the same values）；'
     'STRATA_ATTN_MERGE_V2（qsa_decode_attn.cu:929）；STRATA_EXPDEC（iq_kernels.cu:2432）。'
     'gfx12 表实测四项合计 +3.5%（3/3 对，md5 与默认相同）；P212 的 mega 组只含 TSUM、不含另外三项 ⇒ 三项从未在 gfx906 上测过。'
     '另有纯实现缺口：STRATA_HC_UPMIX（prefill/kernels.cu:2295 gfx11 版 + :2367 sm_80+ 版，无 gfx906 版，纯算子融合）；'
     'STRATA_GDN_CHUNKED（prefill/kernels.cu:1675 仅 __gfx1100__..__gfx1151__，用 wmma_f32_16x16x16_f16_w32，算法可 fp32 重写）；'
     'STRATA_GRAPH_PRIO（core/verify.cpp:219 逐字 #if defined(STRATA_USE_HIP)||defined(STRATA_HIP_GFX906)||defined(STRATA_GPU_METAL) return false；'
     '注释 every HIP caller is guarded off）；conversation checkpoint/park 异步族（#3779 正文逐字 CUDA only, on HIP gfx906 and Metal they are off）。'
     'B 类硬件不符：qsa_select 的 gfx11/gfx12 scorer 用 v_wmma_f32_16x16x16_bf16_w32（gfx906 无 WMMA）、GDN_TC、PF_FUSED_F16。'
     'C 类路径不适用：STRATA_DEQUANT_WIDE 看似纯赚（按 CUDA compute capability 6.1/8.6/8.0 判，HIP 上恒 OFF；'
     'sm_86 短提示 TTFT -12~-17%、sm_80 prompt +4~7%，均 bitwise），但我们在 MMQ_KQ=1 下走 prefill.cpp:1836 '
     'if (mmq_plan().any)，不解包成 bf16 ⇒ 该 dequant 路径用不上，判不适用。',
     '先跑 A 类四项开关的 5 臂 A/B（a13_bitwise.sh），再考虑 HC_UPMIX 的 gfx906 实现。'),
]

for r in rows:
    if ('\n' + r[0] + '\t') in ('\n' + s):
        print(r[0], 'exists')
    else:
        s += '\t'.join(r) + '\n'
        print(r[0], 'added')

io.open(P, 'w', encoding='utf-8', newline='\n').write(s)
print('rows now:', len([l for l in s.split('\n') if l.strip()]) - 1)
