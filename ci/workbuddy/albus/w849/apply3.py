# -*- coding: utf-8 -*-
"""W849：X1 判 NA（上游默认已做）、X2 降级说明；STATUS/记忆追加。"""
import io

ROOT = "D:/workbuddy_space/strata_ws/deploy/"

# ---------- PROGRESS：X1 -> NA，X2 备注 ----------
p = ROOT + "PROGRESS.tsv"
s = io.open(p, encoding="utf-8").read()
lines = s.splitlines()
out = []
n1 = n2 = 0
for ln in lines:
    if ln.startswith("#") or ln.startswith("block\t") or not ln.strip():
        out.append(ln)
        continue
    f = ln.split("\t")
    if len(f) > 1 and f[1] == "X1":
        n1 += 1
        f[6] = "1"
        f[7] = "NA"
        f[8] = ("上游默认已做（W849 实测启动日志）：`--ple-io ram chosen by the residency policy` + "
                "`PLE table loaded (not locked) in 0.2 s` ⇒ 0.2.7 起引擎按内存自动选 ram，W814 的 −8~−23% 早就在吃。"
                "不需要任何改动；显式 `--ple-io direct` 才会退回。")
    if len(f) > 1 and f[1] == "X2":
        n2 += 1
        if f[7] == "OPEN":
            f[8] = ("（W849 评估）容器 ulimit -l=8192KB，26.8 GiB 表锁不住，横幅报 mlock failed；但宿主 125 GB / available 45 GB，"
                    "表已在 RAM 且 pre-touch，未锁的后果仅是压力下可能回收、回收后从 RAM 重读而**不是**回 SSD ⇒ 预期收益 0。"
                    "按纪律不为卫生付 4 min 停服；仅当内存真紧张时再做。")
    out.append("\t".join(f))
s = "\n".join(out) + "\n"
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("X1 -> NA (%d 行), X2 备注 (%d 行)" % (n1, n2))

# ---------- W832 队列：X1 划掉 ----------
p = ROOT + "W832_OPT_PLAN_V2.md"
s = io.open(p, encoding="utf-8").read()
old = "| **2** | **X1 `--ple-io ram` + 启动前 drop_caches（P141）** |"
i = s.find(old)
if i > 0:
    end = s.find("\n", i)
    s = s[:i] + ("| ~~2~~ | ~~**X1 `--ple-io ram`（P141）**~~ **已结（NA，W849）**：引擎 0.2.7 起按内存自动选 `ram`"
                 "（日志 `--ple-io ram chosen by the residency policy`，表 26.8 GiB in RAM）⇒ 无需我们开 | — | — |") + s[end:]
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)
    print("W832 队列 X1 标 NA")
else:
    print("W832 队列未找到 X1 行")

# ---------- STATUS ----------
p = ROOT + "STATUS_2026-10-31.md"
s = io.open(p, encoding="utf-8").read().rstrip()
s += """

## 8 本轮（W849）：分支顶端已复核 + 队列结两条

### 8.1 「在分支顶端」= **已证明，不是声称**

| 检查 | 值 |
|---|---|
| branch / HEAD / tree | `gfx906/0.2.9-mi50` / `aef9d256` / `4ce087ba…` |
| upstream/main（GitHub API 直查） | `c62d5e3a15`（= v0.2.9，committer date 2026-10-31T02:23:01Z）⇒ **上游没前进** |
| ahead/behind upstream | **0 / 1**（我们领先 1 个提交） |
| ahead/behind origin | **0 / 0** |
| 工作区 | dirty **0** |
| **`/src` vs HEAD 树（全量逐文件 md5）** | 5319 / 5319 相同，**diff 0，miss 0** |
| 引擎二进制 vs 构建产物 | `29b15bb4…` == `29b15bb4…` |

固化为一条命令 `~/strata166/tmp/verify_tip.sh`（六项，全过打印 `TIP-OK`，否则退出码 1）；已写进 `SESSION_STATE §7` 与
`PROD_BASELINE`（补 `commit/branch/tree/upstream` 四行）。

### 8.2 队列结两条（零停服）

- **R2 `--vram-reserve-mib 1536` → NA**：专家缓存 **7463 槽 = 全部专家**（`pre-filled 7463 of 7463`）、
  `PROFILE … no eviction`、`cc.evictions=0`、`gpu_pcie_rx_mb` **60 样本恒 0.01 MB**、每请求 `pcie_share` ≤0.004
  ⇒ "cache 太小"这个前提不成立，加大 reserve 只会把缓存变小。
- **X1 `--ple-io ram` → NA**：引擎 0.2.7 起**自己**按内存选 ram：
  `--ple-io ram chosen by the residency policy`（表 26.8 GiB，available 118.9 GiB）+ `PLE table loaded in 0.2 s`
  ⇒ W814 的 −8~−23% 早就在吃，不需要我们动。顺带评估 **X2 mlock**：`ulimit -l=8192KB` 锁不住 26.8 GiB，
  但未锁只是"压力下可能回收、回收后从 RAM 重读"，预期收益 0 ⇒ 不为卫生付停服。

### 8.3 生产

**0 落产**：镜像 `0.2.9t2`、容器 `52a5d5c7b587`、`started 12:46:00Z`、`restarts=0`、`slots=7463 vram_free=920 pcie=0.20`、门禁 PASS 全部未变。
进度 **10 块 / 95 条 / 已结 37（38.9%）**，主线 67 条 55.2%。

### 8.4 下一步

**X15（ROCm 10.1）的零风险段**：造候选镜像（`0.2.9t2` + 10.1 userland），只验 `ldd` / 二进制加载 / `rocBLAS` 是否识别 gfx906；
停服窗口留给正式 A/B + 视结果重 tune rocBLAS 表（换版本表即作废，这窗口躲不掉）。
"""
io.open(p, "w", encoding="utf-8", newline="\n").write(s + "\n")
print("STATUS §8 ok")

# ---------- 记忆 ----------
m = "D:/workbuddy_space/strata_ws/.workbuddy/memory/2026-10-31.md"
t = io.open(m, encoding="utf-8").read().rstrip()
t += """

## W849 分支顶端复核 + R2/X1 结项（20:57–21:10）

- **分支顶端已证明**：`gfx906/0.2.9-mi50 @ aef9d256`，upstream/main（GitHub API 直查）= `c62d5e3a` = v0.2.9（未前进），
  ahead/behind upstream **0/1**、origin **0/0**、dirty **0**；**`/src` 与 HEAD 树全量 5319 文件逐位相同（diff 0 / miss 0）**；
  引擎二进制 == 构建产物 `29b15bb4…`。
- **固化 `~/strata166/tmp/verify_tip.sh`**（六项，`TIP-OK`/退出码）→ 写进 SESSION_STATE §7 + PROD_BASELINE（commit/branch/tree/upstream）。
- **坑**：`docker exec … python3 - <<PY` 不带 `-i` ⇒ stdin 不接入，读到空、输出 0 行（像"镜像里没有文件"）。
  正解：脚本落 `/data` 再 `docker exec python3 /data/x.py`。
- **R2 判 NA**：7463 槽 = 全部专家（pre-filled 7463/7463）、`no eviction`、`evictions=0`、`gpu_pcie_rx_mb` 60 样本恒 0.01 MB、
  `pcie_share` ≤0.004 ⇒ "cache 太小"不成立。
- **X1 判 NA**：引擎 0.2.7 起自己选 `--ple-io ram`（日志 `chosen by the residency policy`，表 26.8 GiB in RAM，0.2 s 载入）
  ⇒ W814 的 −8~−23% 早就在吃。**X2（mlock）**：`ulimit -l=8192KB` 锁不住，但未锁只是可能回收、回收后从 RAM 重读 ⇒ 预期 0，不占停服。
- 生产 **0 落产**；进度 10 块 / 95 条 / 已结 **37（38.9%）**，主线 55.2%，台账欠账 0。
"""
io.open(m, "w", encoding="utf-8", newline="\n").write(t + "\n")
print("memory ok")
