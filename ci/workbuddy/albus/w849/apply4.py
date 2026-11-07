# -*- coding: utf-8 -*-
"""W849b：记录 ROCm 10.1 候选镜像的静态验证结果（X15 进展）+ STATUS/记忆。"""
import io

ROOT = "D:/workbuddy_space/strata_ws/deploy/"

# ---------- PROGRESS X15 ----------
p = ROOT + "PROGRESS.tsv"
s = io.open(p, encoding="utf-8").read()
lines = s.splitlines()
out = []
n = 0
for ln in lines:
    if ln.startswith("#") or ln.startswith("block\t") or not ln.strip():
        out.append(ln)
        continue
    f = ln.split("\t")
    if len(f) > 1 and f[1] == "X15":
        n += 1
        f[8] = ("（W849 静态验证已过）候选镜像 `strata-gfx906:0.2.9r1`（`d4afd5f5…`，15.07 GB）= 0.2.9t2 的 /opt/rocm 整体换成 "
                "ROCm 10.1.0 / HIP 7.16.26323 / rocBLAS 5.7（带 gfx906 内核）。挂真实二进制验：`ldd` **缺失 0**、"
                "librocblas.so.5 / libamdhip64.so.7 / libhipblaslt.so.1 全部解析到新树、`--version` = `strata 0.1.55`。"
                "**未上生产**。剩余：① 停服 A/B（read 六档 + decode）；② rocBLAS 5.5→5.7 使 60 行表作废，"
                "A/B 必须分别量「带表/不带表」，若 10.1 更好再重 tune。门槛 3%。")
    out.append("\t".join(f))
io.open(p, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
print("X15 更新 %d 行" % n)

# ---------- W849 文档追加 ----------
p = ROOT + "W849_TIP_AND_QUEUE.md"
s = io.open(p, encoding="utf-8").read().rstrip()
s += """

---

## 6 X15 进展（本轮做了零风险段）：10.1 候选镜像已过静态验证

按"不碰生产"的约定，只造候选镜像 + 静态验证：

```dockerfile
FROM routek-base:gfx906-rocm101-hip716-torch215-tv030-df1 AS rocm101
FROM strata-gfx906:0.2.9t2
RUN rm -rf /opt/rocm /opt/rocm-*          # base 的 /opt/rocm/bin 等是符号链接，先删再拷，否则
COPY --from=rocm101 /opt/rocm /opt/rocm   # "cannot copy to non-directory"
```

结果 `strata-gfx906:0.2.9r1`（`sha256:d4afd5f5…`，**15.07 GB**，多出来的 6.9 GB 是新 ROCm 树）：

| 检查 | 值 |
|---|---|
| `/opt/rocm/.info/version` | **10.1.0** |
| HIP | **7.16.26323** |
| rocBLAS | **5.7**（`librocblas.so.5.7`） |
| rocBLAS 里 gfx906 内核 | **有** |
| `ldd /in/strata-0.1.55g` | **缺失 0** |
| 关键库解析 | `librocblas.so.5` / `libamdhip64.so.7` / `libhipblaslt.so.1` **全部指向新 /opt/rocm** |
| `--version` | `strata 0.1.55` |

⇒ **现成二进制无需重编即可在 10.1 上加载**。剩下的都是运行期问题，必须在停服窗口里判定：

1. **A/B**：read 六档（2575 / 3014 / 5282 / 5512 / 18980 / 19358）+ decode 3×200 中位；门槛 3%（引擎级 A/B 只判 ≥5%，但同一实例内 A/B 可到 3%）。
2. **表的问题必须一起量**：我们的 60 行表头是 `STRATA_ROCBLAS_TUNING_V1 gfx906 5.5.0.cd957402309`，
   换 rocBLAS 5.7 后**直接失效** ⇒ 要分别测「10.1 + 不带表」与「7.14 + 带表」，否则会把"丢了调优"误读成"ROCm 变慢"。
   若 10.1 更好，再用 `tools/hip` 的 tuner 重打 5.7 的表（这是额外一轮）。

**未上生产**：候选镜像只是躺在本地，`strata166-407` 仍在 `0.2.9t2`（ROCm 7.14）。
"""
io.open(p, "w", encoding="utf-8", newline="\n").write(s + "\n")
print("W849 文档追加 §6")

# ---------- STATUS ----------
p = ROOT + "STATUS_2026-10-31.md"
s = io.open(p, encoding="utf-8").read().rstrip()
s += """

## 9 X15 零风险段完成：ROCm 10.1 候选镜像可加载

`strata-gfx906:0.2.9r1`（`d4afd5f5…`，15.07 GB）：0.2.9t2 的 `/opt/rocm` 整体换成 **ROCm 10.1.0 / HIP 7.16.26323 / rocBLAS 5.7**（带 gfx906 内核）。
挂真实二进制静态验证：`ldd` **缺失 0**，`librocblas.so.5`/`libamdhip64.so.7`/`libhipblaslt.so.1` 全部解析到新树，`--version` = `strata 0.1.55`
⇒ **现成二进制不必重编**。生产未动（仍 0.2.9t2 / ROCm 7.14）。

**下一步（要一个停服窗口，约 20 min）**：A/B「10.1 vs 7.14」，read 六档 + decode，门槛 3%；
**必须同时量"带表/不带表"**——rocBLAS 5.5→5.7 会让 60 行表作废，否则会把"丢了调优"当成"ROCm 变慢"。
"""
io.open(p, "w", encoding="utf-8", newline="\n").write(s + "\n")
print("STATUS §9 ok")

# ---------- 记忆 ----------
m = "D:/workbuddy_space/strata_ws/.workbuddy/memory/2026-10-31.md"
t = io.open(m, encoding="utf-8").read().rstrip()
t += """

## W849b ROCm 10.1 候选镜像静态验证（21:10–21:20）

- 候选 `strata-gfx906:0.2.9r1`（`d4afd5f5…`，15.07 GB）：`FROM routek-base…` 作 rocm101 源，
  **先 `RUN rm -rf /opt/rocm`** 再 `COPY --from=rocm101 /opt/rocm /opt/rocm`（否则 base 的 `/opt/rocm/bin` 符号链接导致
  `cannot copy to non-directory`）。
- 内容：ROCm **10.1.0** / HIP **7.16.26323** / rocBLAS **5.7**（gfx906 内核在）。
- 静态验证（挂真实二进制）：`ldd` 缺失 **0**；librocblas.so.5 / libamdhip64.so.7 / libhipblaslt.so 全解析到新树；`--version` = `strata 0.1.55`
  ⇒ **不必重编**。生产未动。
- 下一步停服 A/B 必须同时量「带表/不带表」：表头绑 `5.5.0.cd957402309`，换 5.7 直接失效。
- 坑：`docker run --rm` 不挂 /data 时 `ldd /data/bin/...` 会空跑（文件不存在但 grep 计数为 0，看着像"通过"）——必须 `-v` 挂载再验。
"""
io.open(m, "w", encoding="utf-8", newline="\n").write(t + "\n")
print("memory ok")
