# -*- coding: utf-8 -*-
"""W850：X15 判否（10.1 as-is），基线更新，STATUS/记忆追加。"""
import io

ROOT = "D:/workbuddy_space/strata_ws/deploy/"

# ---------- PROGRESS：X15 -> REJECTED ----------
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
        f[6] = "1"
        f[7] = "REJECTED"
        f[8] = ("三臂 A/B（W850）：同一二进制同配置只换 /opt/rocm。read 2575/3184/3210/5512/19358 tok："
                "A(7.14) 4492/5636/5884/8155/27823，B(10.1) 5013/5990/6354/8860/28776，A2(7.14) 4502/5669/5992/8175/27847；"
                "A↔A2 离散≤1.8% ⇒ B 比均值 **慢 +11.5/+6.0/+7.0/+8.5/+3.4%**；decode 44.67/46.28/46.10（中性）。"
                "归因见日志：`rocBLAS version mismatch: file=5.5.0.cd957402309 runtime=5.7.0.962d0059; rocBLAS's default kernels run` "
                "⇒ 10.1 把我们的表挡掉了。**不采纳 as-is**；重评估前置=先做 5.7 的表（否则永远是'表 vs 无表'）。"
                "顺带核实 10.1 移除 rocm-smi 不影响我们（遥测读 sysfs）。见 deploy/W850_ROCM_AB.md")
    out.append("\t".join(f))
io.open(p, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
print("X15 -> REJECTED（%d 行）" % n)

# ---------- 基线：容器重建了（id/started 变） ----------
p = ROOT + "PROD_BASELINE.tsv"
b = io.open(p, encoding="utf-8-sig").read()
b = b.replace("started\t2026-10-31T12:46:00.172688628Z", "started\t2026-10-31T13:26:06.958166741Z")
b = b.replace("recorded\t2026-10-31T20:55:00+08:00", "recorded\t2026-10-31T21:32:00+08:00")
if "container_id" not in b:
    b = b.replace("started\t2026-10-31T13:26:06.958166741Z",
                  "started\t2026-10-31T13:26:06.958166741Z\ncontainer_id\tf5a70359b4e8")
io.open(p, "w", encoding="utf-8", newline="\n").write(b)
print("baseline 更新 started/container_id")

# ---------- STATUS ----------
p = ROOT + "STATUS_2026-10-31.md"
s = io.open(p, encoding="utf-8").read().rstrip()
s += """

## 10 ROCm 10.1 三臂 A/B（停服窗口，21:08–21:30）：**判否**

同一二进制、同 33 args / 6 env，只换 `/opt/rocm`；A(7.14) / B(10.1) / A2(7.14) 交错。

| read | A 7.14 | B 10.1 | A2 7.14 | A↔A2 | **B 对均值** |
|---|---:|---:|---:|---:|---:|
| 2575 | 4492 | **5013** | 4502 | −0.2% | **+11.5%** |
| 3184 | 5636 | **5990** | 5669 | −0.6% | **+6.0%** |
| 3210 | 5884 | **6354** | 5992 | −1.8% | **+7.0%** |
| 5512 | 8155 | **8860** | 8175 | −0.2% | **+8.5%** |
| 19358 | 27823 | **28776** | 27847 | −0.09% | **+3.4%** |
| decode 中位 | 44.67 | 46.28 | 46.10 | −3.1% | +2.0%（噪声内） |

**归因（日志原文）**：`rocBLAS version mismatch: file=5.5.0.cd957402309 runtime=5.7.0.962d0059 (/data/gfx906-rocblas-5.5.0.txt); rocBLAS's default kernels run`
⇒ 10.1 的 rocBLAS 5.7 把我们的 60 行表挡掉，跑的是默认解。所以结论只能写到这里：
**"10.1 + 无表"比 "7.14 + 有表" 慢 3.4–11.5%（read）**；表本身历史价值 1.27×（瘦 N 桶），小 prompt 最瘦 ⇒ 与 +11.5% 一致。

**判词**：不采纳 as-is。重评估的前置是**先做 5.7 的表**（否则永远是"表 vs 无表"）；而 10.1 的发布重点是 hipFILE/Infinity Storage、NUMA 内存、ROCm CLI —— Strata 一条都没用到，
官方兼容矩阵也仍无 gfx906（我们自己 TheRock 构建）。候选镜像 `0.2.9r1`（15.07 GB）留作证据。

**顺带**：10.1 移除 `rocm-smi` 一条专门核过 —— 我们的遥测读 **sysfs**（`/sys/class/drm/renderD*/device` + hwmon），不 shell 调 smi；两代镜像里 smi 工具都在。无影响。

**收尾**：生产用 0.2.9t2 重新拉起（ready 258 s），门禁 PASS，`verify_tip.sh` → **TIP-OK**（`aef9d256`，`/src` 5319 文件逐位同）。
**成本**：三臂 21.5 min（242/258/280 s 载入 + 每臂约 60 s 测试）。
**脚本缺陷**：`arm-<label>` 命名是 rename 之前的容器（off-by-one），`arm-A2` 里其实是 B 的容器；数据不受影响，下次要改。
"""
io.open(p, "w", encoding="utf-8", newline="\n").write(s + "\n")
print("STATUS §10 ok")

# ---------- 记忆 ----------
m = "D:/workbuddy_space/strata_ws/.workbuddy/memory/2026-10-31.md"
t = io.open(m, encoding="utf-8").read().rstrip()
t += """

## W850 ROCm 10.1 A/B 判否（21:08–21:30）

- 三臂 A(7.14)/B(10.1)/A2(7.14)，同一二进制同配置只换 /opt/rocm。read（2575/3184/3210/5512/19358 tok）：
  A 4492/5636/5884/8155/27823；B 5013/5990/6354/8860/28776；A2 4502/5669/5992/8175/27847。A↔A2 ≤1.8% ⇒ **B 慢 +11.5/+6.0/+7.0/+8.5/+3.4%**；
  decode 44.67/46.28/46.10（中性）。
- **归因**：`rocBLAS version mismatch: file=5.5.0.cd957402309 runtime=5.7.0.962d0059; rocBLAS's default kernels run`
  ⇒ 10.1 的 rocBLAS 5.7 挡掉我们的 60 行表，跑默认解。结论只能写"10.1+无表 比 7.14+有表 慢 3.4-11.5%"。
- **判否（as-is）**：重评估前置 = 先做 5.7 的表；10.1 的卖点（hipFILE/Infinity Storage、NUMA 主机内存、ROCm CLI）Strata 都没用到；
  官方矩阵仍无 gfx906。候选镜像 0.2.9r1（15.07 GB）留证。
- 顺带：10.1 移除 rocm-smi 不影响我们 —— 遥测读 sysfs，不调 smi。
- 收尾：生产 0.2.9t2 重新拉起（258 s），GATE PASS，**TIP-OK**（aef9d256，/src 5319 逐位同）。
- 脚本缺陷：`arm-<label>` 是 rename 前的容器（off-by-one），`arm-A2` 实为 B 的容器；数据不受影响。
"""
io.open(m, "w", encoding="utf-8", newline="\n").write(t + "\n")
print("memory ok")
