# 修复被 shell 吃坏的 W714c 日志段（重写该段，全部走落盘脚本不经内联 -c）
import io, os

LOG = r"D:/workbuddy_space/strata_ws/.workbuddy/memory/2026-10-08.md"
t = io.open(LOG, encoding="utf-8").read()
i = t.find("## W714c")
if i > 0:
    t = t[:i].rstrip("\n") + "\n"
    print("已截掉损坏的 W714c 段（%d 字符）" % (len(io.open(LOG, encoding='utf-8').read()) - len(t)))

note = """## W714c 机主问：Sumandora/remove-refusals-with-transformers 能不能用（2026-10-09 00:0x，**只做评估，未动任何模型**）
- 仓库实况（GitHub API 实读）：**2,262 star**、Apache-2.0、默认分支 master、最后 push 2025-11-27；**全仓只有 7 个文件**：
  compute_refusal_dir.py (2,984 B) · inference.py (3,599 B) · harmful.txt (38 KB) · harmless.txt (1.9 MB) · requirements.txt · LICENSE · README.md。
  README 自述 "crude, proof-of-concept"、在 RTX 2060 6GB 上**主要测 <3B 模型**、并**点名 Qwen 类可能不工作**
  （原文：model.model.layers can't be used for getting layers）。技术 = 著名的「拒答由单一方向介导」（Arditi 等）=> 方向消融 / abliteration。
- **对 Flash-Next 的可行性：低。三条硬障碍**：
  1. **手上没有它的 HF 原版权重**。实测 D:/IDM 的 model-0000{1..6}-of-00006.safetensors 合计 22.7 GB，config 是
     architectures=Qwen3_5MoeForConditionalGeneration、model_type=qwen3_5_moe、quantization_config=autoround 4-bit
     => 那是 **27B** 那个（不是 Flash-Next）。Flash-Next 的 BF16 原版约 350 GB；166 只剩 251 GB 盘、128 GB RAM => 装不下。
  2. 该实现的层访问路径与 Qwen / MoE 结构不合（README 自己点名），而 Flash-Next 还是 hybrid + MoE（512 专家）=> 必须改代码。
  3. 即便做出 ablated 权重，还要重走整条链：**IQ4_XS 量化（需 imatrix 校准）-> iq_pack 成 Strata pack -> 重建 MTP draft 层**
     => 等于换模型，本项目既有读数全部作废。
- **本机现成的可比资产**（实测）：/models 里有 JonathanColetti/Qwen3.8-27B-Uncensored-{vision-f16,Q4_K_M}.gguf、
  dealignai/Ornith-1.5-35B-A3B-UNCENSORED-GGUF；D:/IDM 里有 Qwen3.8-27B-Uncensored-{Q4_K_M,Q5_K_M}.gguf、
  Ornith-1.5-35B-A3B-CRACK-Q4_K_M.gguf、qwen3vl_32b_heretic_*.safetensors
  （**heretic** = 另一款 abliteration 工具，说明这条路以前在别的模型上走过）。
- **现实路径排序（成本递增）**：a) 找**现成的 Flash-Next abliterated GGUF**（省掉全部量化链）；b) 用本地已有的 uncensored/heretic 资产练手或直接用；
  c) 真要对 Flash-Next 做 -> 先解决约 350 GB 原版权重 + 全链重做；d) 不改权重：服务端行为层（系统提示 / 采样参数）或直接换模型。
- **风险陈述**（不劝，只陈述事实）：166 的服务**同网无鉴权**（PROJECT.md §二 自述「服务无鉴权，同网任何人可用」），
  去拒答权重放上去会直接放大滥用面；改基础模型可能触及模型许可的用途条款（Flash-Next / Qwen 许可需自核）；
  另外下游一切「答案一致性」判据都会整体改变（今天 B1b / B3 的争议已证明这台机器上这一点极敏感）。
- **自伤记录（今天第 4 次同型）**：把含反引号的中文塞进内联 python -c，被本地 shell 做命令替换 => 本段第一次写入被吃坏；
  已按纪律改为**落盘脚本重写**（本条是修复后的版本）。纪律再确认：**任何含反引号 / $( 的文本，一律 Write 落盘再执行，绝不走内联 -c**。
"""
io.open(LOG, "a", encoding="utf-8", newline="\n").write(note)
print("已重写 W714c 段 %d 字符" % len(note))
