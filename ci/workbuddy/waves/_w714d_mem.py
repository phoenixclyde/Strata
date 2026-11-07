# 记 W714d：现成 abliterated Flash-Next GGUF 的存在性 + iq_pack 准入判定（结论级发现）
import io

LOG = r"D:/workbuddy_space/strata_ws/.workbuddy/memory/2026-10-08.md"
note = """
## W714d 反转：现成的 Flash-Next abliterated GGUF 已存在，且正好有 IQ4_XS 档（2026-10-09 00:0x，只读检索）
- 网页检索（2026-10-08）命中三个成品仓：
  1) orcarouter/Qwen3.8-Flash-Next-Uncensored-GGUF：150,668 下载 / 50 个 GGUF / 13 档（IQ2_XXS..Q8_0）；
     其中 **IQ4_XS 三分片 41.69 + 41.66 + 7.42 = 约 90.8 GB**（与我们现役同一量化档）；另带
     Qwen3.8-Flash-Next-Uncensored-MTP-draft.gguf (3.85 GB) 与 vision projector；标 Apache-2.0；**仓库是 gated(auto)，须登录并接受条款**。
  2) huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF：卡片自述**就是用 remove-refusals-with-transformers 做的**（即机主问的那个仓），
     GGUF 由 unsloth/Qwen3.8-Flash-Next-GGUF 转换；Image-Text-to-Text；许可 qwen-community-1.0。
  3) windowsxp811203/Qwen3.8-Flash-Next-Abliterated-GGUF：Q4_K_M 111 GiB / Q5_K_M 125 / Q6_K 156 / Q8_0 175 / BF16 330 GiB；
     **无 MTP**（其转换器 supports_mtp_export=False）；需打补丁的 llama.cpp（PR #27742）。
- 技术细节（orcarouter 博客自述，属其自报数字）：abliteration 作用于 **149 个 residual-writer 张量**；
  **router / 51B n-gram 表 / vision tower 明确未动**；有害拒答 64-100% -> 约 0-3.3%；能力 MMLU-Pro/GSM8K 在 +-2 分内（自报未独立复现）。
- **可落地性判定（本机读源码即可，无需下载）**：tools/iq_pack.py 的 docstring 自述 "a native pack for **any** of the model files"，
  其校验是**结构性**的（分片命名 -0000N-of-0000M.gguf 齐全、general.architecture 在场、张量不重复/不截断、非有限值拒绝），
  **不是两档白名单**；那两档清单只存在于 setup.py（我们不走的下载门）。=> **orcarouter 那种第三方 IQ4_XS 应当可以被 iq_pack 吃下**（待实测）。
- 因此路径成本从"350 GB 原版权重 + 全链量化重做"降为：
  **下载 IQ4_XS 三片(90.8 GB) -> iq_pack 成新 pack -> 新容器 -> 复验**；MTP 很可能可**复用现有 /data/mtp/rt**
  （若 abliteration 只动 residual writers，MTP 头未变）。仍需机主自己做的一件事：**在 HF 上接受 gated 条款**（我无法代做）。
- 风险/约束（陈述）：① 166 仅剩 251 GB 空闲，下载 90.8 GB + pack 约 90 GB 后偏紧（可能要先清旧 pack/本机副本）；
  ② 改权重 => 今日所有"答案一致性"基线整体作废；`--expert-profile`（我们学的 ud-iq4_xs-learned.bin）应按新模型重跑；
  ③ 各仓许可不一（orcarouter 标 Apache-2.0；huihui/windowsxp 标 qwen-community-1.0）—— 基础模型是 Qwen Community License，
  派生分发条款需自核；④ 166 服务同网无鉴权，去拒答权重会直接放大滥用面。
"""
io.open(LOG, "a", encoding="utf-8", newline="\n").write(note)
back = io.open(LOG, encoding="utf-8").read()
for k in ["W714d", "orcarouter", "IQ4_XS 三分片", "149 个 residual-writer", "iq_pack.py", "gated"]:
    print("  自证 %-34s %s" % (k, "OK" if k in back else "**缺失**"))
print("写入 %d 字符" % len(note))
