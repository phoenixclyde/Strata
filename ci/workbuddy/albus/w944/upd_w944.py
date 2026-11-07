# -*- coding: utf-8 -*-
"""W944: add R86 (Q5_1 weight repack, P0) and R87 (q8_1 activation reuse, P1); amend R85 ordering."""
import io

P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"

R86_EV = ("**W944 立（2026-11-04 14:5x）**。**起因**：机主指出只看了 llama.cpp 上游、且不是最新源码，必须参考 gfx906 专门项目。"
          "补查 `mxxm-t/mx-llama.cpp`（原 mixa3607，基线 upstream b11553）后确认漏项：它在 gfx906 默认开 **weight repack**"
          "（quants 与 scales 分平面、行去别名），官方表 **Q5_1 +84%（单卡）/ +74%（双卡 tensor）prefill**、Q6_K +69%、Q5_K +55%、**Q4_K 只 +2~5%**；"
          "并明确写「Qwen3.8-Flash-Next MoE 带 43 个 Q5_1 tensor 该 repack **+11% prefill（四卡）**」。"
          "**本机格式分布**（native_experts.txt，48 层 x 512 专家）：gu = Q4_K 47 层 + Q5_K 1 层；down = **Q5_1 43 层（88.6% 专家字节）** + Q8_0 5 层"
          " ⇒ 我们最重的格式正好是外证收益最高的那档。**预期** down kernel +84% ⇒ 端到端 **-6.3%**（down 占 prefill 13.8%）；只拿一半 ⇒ -3.2% 仍在门上。"
          "**数值**：mx 记录 Q5_1 单卡输出逐字节相同 ⇒ 预期无需 KL 门，仍跑一次 logits 对比。**路径断言**：repacked stride == repack_gcn_nbytes(Q5_1,640,2560)；"
          "down 内核 v_add_u32/v_mul_lo_u32（本机整 kernel 占 19.7%）显著下降；日志 0 reused。"
          "**工程关键**：我们是按需上传（prefill 每 chunk 借 2606 槽 = 7.62 GiB），repack 必须在上传后就地做（GPU 侧一次核），不能假设全模型常驻。"
          "**改动面**：moe_mmq_tab.cuh 的 expert_bytes 步进改 expert_stride、vec_dot_q5_1_q8_1_impl_mmq 换 repacked 读法、新增 repack kernel（约 60 行）。"
          "**第一步**：扩展 kq_bench 跑 canonical vs repacked 两臂（本机形状 640x2560、每专家约 320 token，不是 mx 的 27B dense）；单内核 <20% 判否、>=40% 才动生产。")

R87_EV = ("**W944 立（2026-11-04 14:5x）**。来源 mx-llama.cpp 的 quantized activation reuse：同一 attn_norm 输出被 q/k/v 各量化一次、ffn_norm 被 router 与 gate/up 各一次；"
          "缓存那份 q8_1 可省重复量化，外证 **+2.2~2.6% prefill 与 decode 且 bit-exact**（默认开，GGML_CUDA_Q8_1_CACHE=0 可关）。"
          "本机现状：`mmq::quantize` 在单 product 的 PMC 里只占 1.4%，但整请求每层被调用多次 ⇒ 先量「每请求量化总时间」，若 <1% 则不做（判据 |d|>=2xCV）。")

R85_ADD = (" 【W944】手段排序改为 **R86（Q5_1 repack）> R46（attn 效率）> R64（Q.K int8）**：repack 有 byte-identical 记录、风险低于改 attention 数值，"
           "且外证在本模型上给 +11% prefill（四卡）。上轮「MMQ 五门全关 ⇒ 只剩 attention」撤回——正确的说法是**指令层五门全关，布局层从未开门**。")

row86 = ["B5本机缺口", "R86",
         "Q5_1 down 的权重布局重排（两平面 + 第五位 word + half2 d/m，行去别名）：43/48 层、88.6% 专家字节，外证 mx Q5_1 +84% 单卡 / 本模型 +11% 四卡 prefill",
         "W944 §5", "count", "1", "0", "OPEN", R86_EV, "W944;mx-llama.cpp"]
row87 = ["B6判定探针", "R87",
         "q8_1 激活复用：同一 norm 输出被 q/k/v 与 router+gate/up 重复量化，缓存那份 q8_1（外证 +2.2~2.6%，bit-exact）；先量每请求量化总时间",
         "W944 §6", "count", "1", "0", "OPEN", R87_EV, "W944;mx-llama.cpp"]

with io.open(P, encoding="utf-8", newline="") as f:
    lines = f.read().split("\n")

out, changed = [], []
for ln in lines:
    if "\t" in ln:
        f8 = ln.split("\t")
        if len(f8) >= 9 and f8[1] == "R85":
            f8[8] += R85_ADD; changed.append("R85"); ln = "\t".join(f8)
    out.append(ln)

while out and out[-1] == "":
    out.pop()
out.append("\t".join(row86))
out.append("\t".join(row87))
out.append("")

with io.open(P, "w", encoding="utf-8", newline="") as f:
    f.write("\n".join(out))
print("changed:", changed, "added R86/R87")
