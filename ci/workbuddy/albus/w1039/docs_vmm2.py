#!/usr/bin/env python3
"""W1039: the external document that contradicts the probe - land it as a row + a report paragraph."""
import io

P = "deploy/PROGRESS.tsv"
row = ("B1参数轴", "P475", "外部文档说「gfx906 没有 VMM，任何 ROCm 版本都修不了」，与本卡实测相反：那是 ROCm 6.4 时代的结论，我们这套 10.1 自建树上 VMM 与 `hipMemGetInfo` 都正常",
       "W1039", "count", "1", "1", "DONE",
       "**外部（2026-03-20，FlexInfer gfx906 文档，ROCm 6.4.1 / Radeon VII）**：`hipMemGetInfo() returns hipErrorInvalidValue on gfx906 because the underlying VMM API is not available on Vega20 hardware. This is a hardware limitation ... cannot be fixed in any ROCm version`，并把 `VMM: no` 写成设备事实。"
       "**本机实测（同一设备标识 `gfx906:sramecc+:xnack-`，MI50 32 GB，ROCm 10.1.0 + 自建 gfx906 树）**：属性 **1**、`hipMemGetInfo` 返回 882/32752 MiB、reserve/create/map/setaccess/归还 **全对**。"
       "⇒ 两条都不假，**假的是「与版本无关」这个隐含前提**：gfx906 的 VMM 在 6.4 时代确实缺（该文档没编造），在我们这套树上有。"
       "**判据**：涉及 gfx906 能力的文档结论一律按「版本 + 具体卡」读，**以本机探针为准**；这也是本轮探针法第二次救场（第一次是 `P465` 分数 1.8e-7）。",
       "P472", "KW:FlexInfer|版本无关|探针")

lines = io.open(P, encoding="utf-8").read().splitlines()
lines.append("\t".join(row))
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
print("appended P475")

R = "albus/w1039/reply.md"
r = io.open(R, encoding="utf-8").read()
para = """
**外部核对反而给出一条更值钱的教训（`P475`）**：FlexInfer 的 gfx906 文档（2026-03-20，ROCm 6.4.1 / Radeon VII）明确写 `hipMemGetInfo() returns hipErrorInvalidValue on gfx906 because the underlying VMM API is not available on Vega20 hardware ... cannot be fixed in any ROCm version`，并把「VMM: no」当设备事实。**而我们这台同一设备标识（`gfx906:sramecc+:xnack-`）上，属性是 1、`hipMemGetInfo` 正常返回、整套 VMM 全对。** 两条都不假——假的是「与版本无关」这个隐含前提：6.4 时代 gfx906 确实缺，我们这套 10.1 自建树上有。**判据：gfx906 的能力结论一律按「版本 + 具体卡」读，以本机探针为准。**

**顺带的旁证（与 R104 的方向一致，不是依据）**：vLLM 的 PagedAttention 与 `--max-model-len` 相关讨论反复说明同一件事——**按最大长度预分配 KV 是浪费，按需分配是标准做法**；同时也印证了代价面：预留越少，长请求到来时越要现拿现用。
"""
j = r.find("**但代价面必须一起测**")
assert j > 0
k = r.find("\n", r.find("看它是否真的从缓存拿 chunk、有没有 `could not map`。", j))
r = r[:k] + para + r[k:]
io.open(R, "w", encoding="utf-8", newline="\n").write(r)
print("report §23: external paragraph inserted")

# plan: one line under the W1039 §十四 block
PL = "deploy/W832_OPT_PLAN_V2.md"
p = io.open(PL, encoding="utf-8").read()
a = "- **停机**：窗口两次重启（装机 + 还原），每次 ≈45 s"
assert a in p
p = p.replace(a, "- **外部**：FlexInfer 文档称 gfx906「VMM 不可用、任何 ROCm 都修不了」（ROCm 6.4.1）——与本卡实测相反，**版本相关**（`P475`）。\n" + a, 1)
p = p.replace("**417 条 / 已结 330 / 79.1%**", "**418 条 / 已结 331 / 79.2%**", 1)
io.open(PL, "w", encoding="utf-8", newline="\n").write(p)
print("plan: §十四 += external line, denom -> 418/331")

r2 = io.open(R, encoding="utf-8").read()
r2 = r2.replace("**417 条 / 已结 330 / 79.1%**（本轮 +30：`P445`–`P474`）", "**418 条 / 已结 331 / 79.2%**（本轮 +31：`P445`–`P475`）", 1)
io.open(R, "w", encoding="utf-8", newline="\n").write(r2)
print("report: §四 -> 418/331")
