# 记 W714r：模型归属重锤（全量 sha256）+ 更正 W714g 的抽样判据错误
import io, re

LOG = r"D:/workbuddy_space/strata_ws/.workbuddy/memory/2026-10-08.md"
note = """
## W714r 模型归属重锤 + 更正 W714g 判据（2026-10-09 00:2x-）
- **重锤（166 现场全量 sha256，不是抽样）**：现役主体三片 = 5ce89370 / 577a38a2 / d4634e6d，
  = 官方 unsloth base（unsloth/Qwen3.8-Flash-Next-GGUF 的 UD-IQ4_XS）；166 上跑一遍 313 s。
- **D 盘那份（D:/Qwen3.8-Flash-Next-UD-IQ4_XS）全量 = c67b468b / 130560b6**，
  = huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF 的 unsloth-UD-IQ4_XS。=> 机主下的确实是 abliterated，机主说法正确。
- **更正 W714g（判据错误，重要教训）**：base 与 abliterated 的 00002/00003 **两仓 size 完全相同，
  且 head/mid/tail 三处各 16MB 抽样也完全相同** => "抽样对撞"对这两版**失效**。
  W714g 拿"D 盘与现役抽样全同"推出"D 盘也是 base"，**结论错**。
  **唯一可判据 = 全量 sha256**；两个候选值均已用 hf-mirror 两仓 LFS oid 独立坐实（base 577a38a2/d4634e6d vs huihui c67b468b/130560b6）。
  推广：以后凡"确认 GGUF 归属"，**不许再用抽样哈希**，一律全量 sha256 对 LFS oid。
- **现役其实是混合体**：主体三片 = base（我早先从 ModelScope 下的那份，经 166 内部 ln -f 落到 /models/unsloth，
  与 /home/albus/strata166/weights 同 inode）；**mmproj = huihui**（b1a82259，真传自 D 盘）。
  机主"你现在用的那个 vision 的 draft 也是 huihui 的"**完全正确**。
- 两仓 mmproj 也不是同一个文件：base 是 mmproj-BF16.gguf(2e788f8c, 907542944)；huihui 是 mmproj-Qwen3.8-Flash-Next-BF16.gguf(b1a82259, 907543008)。
- **本机->166 通道实测**：ssh 原始字节 8 进程并行 **89 MB/s** 最优；scp 单流 49；ssh 原始单流 64；base64+线程 39~60。
  11 个样本远端 md5 全等于本机 => 无损。**传输一律用 ssh 原始字节 + 进程并行，不要用 base64 包裹**（GIL 瓶颈）。
- **归位动作**：把 D 盘 00002/00003 真传到 /models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/unsloth-UD-IQ4_XS/
  （00001 两仓相同已在位、mmproj 已在位）。做法：块 2GiB，8 进程并行，`dd of=F bs=1M seek=K conv=notrunc` 按偏移直写（无 part 中转，峰值只占目标文件本身）。
- **切换现役到 huihui 的成本（已核）**：`--pack /data/packs/ud-iq4_xs`(1.4GB: dense.bin/index.txt/native_experts.txt/tokenizer)
  是**从 native GGUF 提取的 301 个投影矩阵**，与 native 强耦合 => 换 native **必须用 /src/tools/iq_pack.py 重生成 pack**；
  另需重跑 expert-profile、既有 benchmark 读数作废；`--mtp /data/mtp/rt` 是官方 Qwen base 派生 => 换 abliterated 主模型后**推测解码接受率待测**。
"""
old = io.open(LOG, encoding="utf-8").read()
with io.open(LOG, "a", encoding="utf-8", newline="\n") as f:
    f.write(note)
back = io.open(LOG, encoding="utf-8").read()
BAN = [0x21D2, 0x2192, 0x2014, 0x2013, 0x2026, 0x2265, 0x2264, 0x2260, 0x2212, 0x00D7]
bad = [(i, hex(ord(c))) for i, c in enumerate(note) if ord(c) in BAN]
cr = back.count("\r")
print("追加 %d 字符；文件现 %d 字符；CR=%d；禁用码位=%d" % (len(note), len(back), cr, len(bad)))
for k in ["W714r", "577a38a2", "c67b468b", "抽样对撞", "iq_pack.py", "89 MB/s"]:
    print("  自证 %-16s %s" % (k, "OK" if k in back else "**缺失**"))
if bad:
    print("  !! 禁用码位:", bad[:10])
