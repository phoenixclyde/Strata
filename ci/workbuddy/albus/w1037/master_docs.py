import io, shutil

# ---- recipe ----
P0 = "deploy/REBUILD_RECIPE.tsv"
shutil.copyfile(P0, P0 + ".bak_mstr")
s0 = io.open(P0, encoding="utf-8").read()
if "strata-0.1.57-mstr" not in s0:
    s0 = s0.rstrip("\n") + "\n" + (
        "strata-0.1.57-mstr\td24f8293b575fbcee6c097239d9599cb\t43207464\tgfx906/lcpp-k10 @ fa8e6761\t"
        "bcb0152876e8f0b684ba70d3defcab6cdf35adb5（master，2026-11-06）\t4c1004c49221b07c3b8108977e3d1991fc9f45cc\t"
        "build-masterp（/src=pr/k10，/llama.cpp=tmp/w1037/llama-master）\t"
        "master 候选，**未装机**；TQ overlay ON；见 P439\n")
    io.open(P0, "w", encoding="utf-8", newline="\n").write(s0)
print("recipe +1")

# ---- ledger ----
P = "deploy/PROGRESS.tsv"
shutil.copyfile(P, P + ".bak_mstr")
s = io.open(P, encoding="utf-8").read()
r = "\t".join([
    "B10环境与版本", "P439",
    "能升到最新：master bcb01528 + mmq@4c1004c 编译通过、**零 API 改动**（d24f8293 / 43,207,464 B），但 70 个提交里 4 条碰我们热路径",
    "W1037", "count", "1", "1", "DONE",
    "**W1037 立（机主：「还能升级最新的吗」）**：llama.cpp master = `bcb0152876e8f0b684ba70d3defcab6cdf35adb5`（2026-11-06T22:42:46Z）；"
    "b12110 = `cd959bae99ff4bed22bef2604f45241c09bbb8c8`；两者相距 **70 个提交 / 300 个文件**。"
    "按 K10 的同一配方（master 全树 + `ggml/src/ggml-cuda/mmq*` 钉回 `4c1004c`）**编译通过，且一行 API 都不用再改**"
    "（`pr/k10` 的 6 处适配原样可用）；候选 `/data/bin/strata-0.1.57-mstr` = `d24f8293b575fbcee6c097239d9599cb` / 43,207,464 B（未装机）。"
    "**但收益不白给**：70 个提交里碰我们热路径的有 4 条——`#31047`（MoE tile_spec，已判否三次：`P356`/`P359`/`P374`，数值不同 + 2K 503）、"
    "`#31296`（NVFP4 gate/up+GLU 融合，同族的 `#29948` 曾让我们 −5%）、`#31660`（MTP conv 快照）、`#30541`（量化 KV 的 state copy 尺寸）。"
    "其余大量是 metal/hexagon/vulkan/opencl/webgpu 与模型支持，对我们零影响。⇒ **能升，但要靠一次窗口判**；"
    "`R99`（升到 b12169）当年就是这条路上 −4.0/−4.6% 挂的。",
    "P438", "KW:master|零 API 改动"])

out = s.rstrip("\n") + "\n" + r + "\n"
io.open(P, "w", encoding="utf-8", newline="\n").write(out)
print("ledger +1 (P439)")

# ---- W832 ----
P2 = "deploy/W832_OPT_PLAN_V2.md"
shutil.copyfile(P2, P2 + ".bak_mstr")
s2 = io.open(P2, encoding="utf-8").read()
a = "**380 条 / 已结 297 / 78.2%**（W1037 校正"
b = "**381 条 / 已结 298 / 78.2%**（W1037 校正"
assert a in s2
s2 = s2.replace(a, b, 1)
ADD = """
**十六、能不能升到最新？能编，代价与收益都不白给（`P439`）。**
master = `bcb0152876e8f0b684ba70d3defcab6cdf35adb5`（2026-11-06T22:42:46Z），距 b12110（`cd959bae`）**70 个提交 / 300 个文件**。
按 K10 同一配方（master 全树 + `mmq*` 钉回 `4c1004c`）**编译通过、零 API 改动**（`pr/k10` 那 6 处适配原样可用），
候选 `/data/bin/strata-0.1.57-mstr` = `d24f8293b575fbcee6c097239d9599cb` / 43,207,464 B（未装机）。

| 提交 | 是否碰我们 | 已有判决 |
|---|---|---|
| `#31047` CUDA: linearize MoE data layout | **是**（MoE 分派） | 已判否三次（`P356`/`P359`/`P374`：需重写分派层、数值不同、2K 503） |
| `#31296` CUDA: fuse NVFP4 gate/up + GLU | 是（同族 `#29948` 曾 −5%） | 我们用 Q4_K，不直接命中，但同一段融合代码 |
| `#31660` graph: MTP conv 快照 | 是（我们开 `--mtp`） | 未测 |
| `#30541` 量化 KV 的 on-device state copy 尺寸 | 是（`--kv k8v4`） | 未测 |
| 其余 ≈60 条 | 否（metal/hexagon/vulkan/opencl/webgpu/模型支持） | — |

⇒ **能升，但必须靠一次窗口判**；`R99`（升 b12169）当年就是在这条路上 −4.0/−4.6% 挂掉的，不能凭「编译过了」就装。
"""
s2 = s2.rstrip("\n") + "\n" + ADD
io.open(P2, "w", encoding="utf-8", newline="\n").write(s2)
print("W832 +十六")

# ---- reply ----
P3 = "albus/w1037/reply.md"
s3 = io.open(P3, encoding="utf-8").read()
a3 = "**380 条 / 已结 297 / 78.2%**（W1037 校正；本轮 +14：`P425`–`P438`）。"
b3 = "**381 条 / 已结 298 / 78.2%**（W1037 校正；本轮 +15：`P425`–`P439`）。"
assert a3 in s3
s3 = s3.replace(a3, b3, 1)
ADD3 = """
**17. 还能升到最新吗？能编，收益要窗口判（`P439`）。**
master = `bcb0152876e8f0b684ba70d3defcab6cdf35adb5`（2026-11-06T22:42），距 b12110 **70 个提交 / 300 个文件**。
按同一配方（master 全树 + `mmq*` 钉 `4c1004c`）**编译通过、零 API 改动**，候选 `/data/bin/strata-0.1.57-mstr`
= `d24f8293b575fbcee6c097239d9599cb` / 43,207,464 B（未装机）。碰我们热路径的只有 4 条：`#31047`（已判否三次）、
`#31296`（NVFP4 融合，同族 `#29948` 曾 −5%）、`#31660`（MTP conv 快照）、`#30541`（量化 KV state copy）。
其余 ≈60 条是别的后端与模型支持。⇒ **能升，但 `R99` 就是在这条路上 −4.0/−4.6% 挂的，不能凭「编译过了」就装。**
"""
s3 = s3.rstrip("\n") + "\n" + ADD3
io.open(P3, "w", encoding="utf-8", newline="\n").write(s3)
print("reply +17")
