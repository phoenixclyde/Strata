# 记 W714g：huihui 仓可下性 + 我们那份的最终定案（全量 sha256 对撞）+ 纠正上一条判据不足
import io

LOG = r"D:/workbuddy_space/strata_ws/.workbuddy/memory/2026-10-08.md"
note = """
## W714g huihui 仓能不能下 + 我们那份的最终定案（2026-10-09 00:1x-00:25）
- **通道**：ModelScope 上**没有** huihui / orcarouter 这几个仓的镜像（详情与文件列表 API 均实测 404）；
  但 **hf-mirror.com 从本机是通的**（API 2.3s 返回 JSON）=＞ HF 那边的东西要走 hf-mirror 下（速度待测）。
- **huihui 仓确实可下且未 gated**：huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF
  （gated=False、license=other、**270,998 下载**、lastModified 2026-10-08），另有纯 transformers 仓
  huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated（safetensors / qwen4_exp / image-text-to-text）。
  仓内布局：BF16(8 片) / Q8_0(6) / UD-Q4_K_XL(4) / unsloth-UD-Q4_K_XL(4) / swift-IQ2_XS(2) / swift-IQ3_XXS(2)
  / **unsloth-UD-IQ4_XS(3)** 与三个 mmproj 变体。
- **关键：abliterated 重量化后 size 不变、只有内容变**。对照表（hf-mirror 给出的 lfs oid 与上游 setup.py 钉死值）：
  unsloth-UD-IQ4_XS 00001：size 同 base、sha256 **完全一致**（5ce89370...）——该片是元数据/分词器部分，未被动；
  unsloth-UD-IQ4_XS 00002：size 同 base（49835229856）、sha256 **不同**（huihui c67b468b... vs base 577a38a2...）；
  unsloth-UD-IQ4_XS 00003：size 同 base（43836407744）、sha256 **不同**（huihui 130560b6... vs base d4634e6d...）。
  =＞ **所以"看 size + 看分片 1 哈希"根本分不出 base 与 abliterated**（我 W714f 的判据不足，此条更正）。
- **最终定案（全量 sha256，166 上在跑的那份）**：分片 2 = 577a38a2392b40ca2193cea502e1d92f60b8cd370675d308e0ec21885d9daaa7（= base 钉死值）、
  分片 3 = d4634e6d84f0ebb0940be15c90d3790bf6464e3dea3a1cddc567dc0e83ad8833（= base 钉死值）；分片 1 早已一致。
  =＞ **现役模型 = 官方 Unsloth base 的 UD-IQ4_XS，三片全部与上游钉死值逐字节相同；不是 abliterated。**
  机主新下的那个目录与现役同源（抽样全同）=＞ 也是 base，**机主手上还没有 abliterated 权重**。
- 落地路径（若机主要 abliterated）：走 **hf-mirror** 下 huihui 的 unsloth-UD-IQ4_XS 三片（约 90.8 GB，正好我们这一档），
  下完逐片 sha256 对撞 hf-mirror 列出的 oid（c67b468b... / 130560b6... / 5ce89370...）=> iq_pack 成新 pack -> 新容器 -> 复验。
  省流做法：**先下 00003 单片（43.8 GB）验证 hf-mirror 速度 + sha256**，通过再下另两片。
- 约束重申：换权重 = 换模型（既有读数作废、expert-profile 需重跑）；166 服务同网无鉴权；huihui 仓 license 标 other（基础模型为 Qwen Community License，需自核派生条款）。
"""
io.open(LOG, "a", encoding="utf-8", newline="\n").write(note)
back = io.open(LOG, encoding="utf-8").read()
for k in ["W714g", "hf-mirror.com 从本机是通的", "270,998 下载", "577a38a2392b40ca", "130560b6", "不是 abliterated", "W714f 的判据不足"]:
    print("  自证 %-34s %s" % (k, "OK" if k in back else "**缺失**"))
print("写入 %d 字符" % len(note))
