# 终修 W714c：全部用直引号、不用反引号；写后逐条自证关键串在场
import io, os

LOG = r"D:/workbuddy_space/strata_ws/.workbuddy/memory/2026-10-08.md"
t = io.open(LOG, encoding="utf-8").read()
i = t.find("## W714c")
if i > 0:
    t = t[:i].rstrip("\n") + "\n"
    io.open(LOG, "w", encoding="utf-8", newline="\n").write(t)

note = """## W714c 机主问 remove-refusals-with-transformers 能不能用（2026-10-09 00:0x，只做评估，未动任何模型）
- 仓库实况（GitHub API 实读）：Sumandora/remove-refusals-with-transformers，2262 star，Apache-2.0，默认分支 master，
  最后 push 2025-11-27；全仓只有 7 个文件：compute_refusal_dir.py(2984 B)、inference.py(3599 B)、
  harmful.txt(38 KB)、harmless.txt(1.9 MB)、requirements.txt、LICENSE、README.md。
  README 自述 "crude, proof-of-concept"，在 RTX 2060 6GB 上主要测 <3B 模型，并点名 Qwen 类可能不工作
  （原文 model.model.layers can't be used for getting layers）。技术 = 「拒答由单一方向介导」（Arditi 等）=> 方向消融 / abliteration。
- 对 Flash-Next 的可行性：低。三条硬障碍：
  1) 手上没有它的 HF 原版权重。实测 D:/IDM/model-0000{1..6}-of-00006.safetensors 合计 22.7 GB，
     config 是 architectures=Qwen3_5MoeForConditionalGeneration、model_type=qwen3_5_moe、quantization_config=autoround 4-bit
     => 那是 27B 那个，不是 Flash-Next。Flash-Next BF16 原版约 350 GB；166 只剩 251 GB 盘、128 GB RAM => 装不下。
  2) 该实现的层访问路径与 Qwen / MoE 结构不合（README 自认），Flash-Next 还是 hybrid + MoE（512 专家）=> 必须改代码。
  3) 即便做出 ablated 权重，还要重走整条链：IQ4_XS 量化（需 imatrix 校准）-> iq_pack 成 Strata pack -> 重建 MTP draft 层
     => 等于换模型，本项目既有读数全部作废。
- 本机现成可比资产（实测）：/models 下有 JonathanColetti/Qwen3.8-27B-Uncensored-vision-f16.gguf 与
  Qwen3.8-27B-Uncensored-Q4_K_M.gguf、dealignai/Ornith-1.5-35B-A3B-UNCENSORED-GGUF；D:/IDM 下有
  Qwen3.8-27B-Uncensored-Q4_K_M.gguf 与 Q5_K_M.gguf、Ornith-1.5-35B-A3B-CRACK-Q4_K_M.gguf、
  qwen3vl_32b_heretic_*.safetensors（heretic = 另一款 abliteration 工具，说明这条路以前在别的模型上走过）。
- 现实路径排序（成本递增）：a) 找现成的 Flash-Next abliterated GGUF（省掉全部量化链）；b) 用本地已有 uncensored/heretic 资产练手或直接用；
  c) 真要对 Flash-Next 做，先解决约 350 GB 原版权重 + 全链重做；d) 不改权重：服务端行为层（系统提示 / 采样参数）或直接换模型。
- 风险陈述（不劝，只陈述事实）：166 服务同网无鉴权（PROJECT.md 第二节自述「服务无鉴权，同网任何人可用」），
  去拒答权重放上去会直接放大滥用面；改基础模型可能触及模型许可的用途条款（Flash-Next / Qwen 许可需自核）；
  下游一切「答案一致性」判据都会整体改变（今天 B1b / B3 的争议已证明这台机器上这一点极敏感）。
- 自伤记录（今天第 4 次同型）：把含反引号的中文塞进内联 python -c，被本地 shell 做命令替换，本段头两次写入均被吃坏；
  现改为落盘脚本 + 完全不用反引号，并逐条自证关键串在场。纪律再确认：含反引号或 $() 的文本一律 Write 落盘再执行，绝不走内联 -c。
"""
io.open(LOG, "a", encoding="utf-8", newline="\n").write(note)

# 逐条自证
back = io.open(LOG, encoding="utf-8").read()
keys = ["W714c", "2262 star", "compute_refusal_dir.py", "master", "Qwen3_5MoeForConditionalGeneration",
        "350 GB", "heretic", "无鉴权", "第 4 次同型"]
print("写入 %d 字符" % len(note))
for k in keys:
    print("  自证 %-42s %s" % (k, "OK" if k in back else "**缺失**"))
print("本段反引号数量:", back[back.find("## W714c"):].count("`"))
