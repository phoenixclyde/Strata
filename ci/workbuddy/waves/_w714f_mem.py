# 记 W714f：权重出处定案（与上游 setup.py 钉死值对撞）+ 纠正"新下的是 abliterated"这一假设
import io

LOG = r"D:/workbuddy_space/strata_ws/.workbuddy/memory/2026-10-08.md"
note = """
## W714f 权重出处定案（2026-10-09 00:1x，机主问「你手里下载哪的」）
- **我们的出处（有据）**：deploy/scripts/_ms_dl_iq4xs.py 里写死 REPO = unsloth/Qwen3.8-Flash-Next-GGUF、
  BASE = https://www.modelscope.cn/models/<REPO>/resolve/master/ ，且走 **Content-Range 硬校验 + 断点续传 + 8 并发**；
  当年记录（deploy/scripts/_append_mem35/36/39.py）另注明"按 setup.py 的 UNSLOTH_*_SHARDS 钉死值逐个核 sha256"。
  => 我们这批权重是从 **ModelScope 的 unsloth 官方 base 仓**下的，并且**逐片 sha256 与上游钉死值比对过**。
- **硬判定**：上游 setup.py 钉死了官方 base 的三片指纹 UNSLOTH_IQ4_XS_SHARDS：
  00001 (10946624, 5ce89370720f8bf90890f439361282104c1aa1482d4013bb9a50923e758e71a4)、
  00002 (49835229856, 577a38a2...)、00003 (43836407744, d4634e6d...)。
  实测本机那份（= D:/IDM/Strata-UDIQ4XS = 机主新下的 D:/Qwen3.8-Flash-Next-UD-IQ4_XS）：
  **分片1 全量 sha256 = 5ce89370720f8bf90890f439361282104c1aa1482d4013bb9a50923e758e71a4（与钉死值完全一致）**，
  分片2/3 的 size 也**逐字节等于**钉死 size（49835229856 / 43836407744）。
  => **我们跑的、以及机主那份"新下载"，都是官方 Unsloth base 的 UD-IQ4_XS，不是 abliterated 版。**
- 由此纠正两个假设：① "166 三天前起跑的可能已经是 abliterated" —— **不成立**；
  ② 机主说"新下的是 huihui-ai/...-abliterated-GGUF" —— **与盘上字节不符**（要么那份实际来自 base/镜像，
  要么该仓的 GGUF 文件本身就是 base 的转换件；其卡片那句 "llama.cpp GGUFs come from unsloth/Qwen3.8-Flash-Next-GGUF" 正指向后者）。
- 未验证：huihui 那个仓里 UD-IQ4_XS 三片的 sha256/size（本机与 166 都到不了 huggingface.co：166 出网实测 HF/MS/GitHub 全不通）。
  可行的独立核法：机主查自家下载器的 URL/历史记录；或改从 ModelScope 镜像该仓（若有）再比 size。
- 结论：**手上还没有任何 abliterated 权重**。要拿到，仍是那三条路（orcarouter 的现成 abliterated IQ4_XS（gated）／huihui 的 BF16 自行量化（重）／换小模型练手）。
"""
io.open(LOG, "a", encoding="utf-8", newline="\n").write(note)
back = io.open(LOG, encoding="utf-8").read()
for k in ["W714f", "_ms_dl_iq4xs.py", "5ce89370720f8bf9", "UNSLOTH_IQ4_XS_SHARDS", "不是 abliterated", "手上还没有任何 abliterated"]:
    print("  自证 %-36s %s" % (k, "OK" if k in back else "**缺失**"))
print("写入 %d 字符" % len(note))
