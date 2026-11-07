import io, os
os.chdir(r"D:/workbuddy_space/strata_ws/deploy")

# ---- 1) W920 追加 PLE mlock 实测 ----
add = """

---

## 7 R67 实测：PLE 表锁定 —— **零收益，已回滚**（2026-11-03 22:5x–23:2x）

### 7.1 做成了，而且证据干净

按 §2 的方案重建容器（逐字段复现：`bridge` / `ipc=host` / `shm 64 MiB` / `group-add video` /
`security-opt label=disable` / `kfd+dri` / 两条 bind / `unless-stopped` / 7 项 env / 同一条 Cmd），
只加 `--ulimit memlock=-1`。结果：

```
HostConfig.Ulimits = [{"Name":"memlock","Hard":-1,"Soft":-1}]
ulimit -l          = unlimited
VmLck              = 28,125,140 kB  (26.82 GiB)   ← 正好是 PLE 表大小
日志               = strata generate: PLE table locked in RAM ... in 1.7 s   （不再是 "not locked"）
```

### 7.2 但收益为零，代价是真的

| 指标 | 旧容器（未锁） | 新容器（已锁） |
|---|---|---|
| prefill median | 8.843 s | 8.860 s（持平） |
| decode 稳定段（后 3 次） | 79.04 | 79.48（+0.6%，噪声内） |
| decode 冷启第一次 | 69.64 | 48.95（−30%） |
| decode CV | 2.2% | 14.4% |
| 宿主 available | 43 GB | **18 GB** |

### 7.3 为什么上游说 6%，我们却是 0：两条前提我们都不成立

1. **上游的前提是"表被反复回收"**（reporters 的场景内存紧张）。我们 `available 43 GB`、PLE 页 faulted-in
   后一直没被回收，"未锁"与"已锁"在稳定期等价。
2. **我们付不起锁定的 RAM 代价**：`PLE 26.82 + 专家 arena 71.73 = 98.55 GiB`，机器只有 125 GB，
   锁完只剩 18 GB ⇒ 专家 arena 的 hugepage 路线更没戏（见 §7.4）。

### 7.4 纠一个我自己的错误归因（重要）

我一度以为"专家 arena 从 page-locked 退化成 file cache"是 PLE 锁定造成的。**不是。**
日志里 `expert arena read through the file cache (buffered (not Windows))` 从 **11-03 13:01 的 run 就开始了**
（行 106800 起每一次启动都是），比本次实验早 10 小时。两臂在这一点上本来就相同 ⇒
**冷启差异不是 PLE 造成的，而是两臂的专家 cache 预热状态不同**（旧容器跑过 W916 + 基线，新容器是全冷）。

### 7.5 但顺着这条线发现了一个真问题：**hugepage 一个都没有**

```
strata generate: expert arena: cudaHostRegister PORTABLE ok;
                 MAP_HUGETLB unavailable (needed 36727 2 MiB pages, vm.nr_hugepages=0);
                 transparent huge pages requested (MADV_HUGEPAGE)
```

引擎想要 **36,727 个 2 MiB 页 = 71.7 GiB** 的显式 hugepage，宿主 `vm.nr_hugepages=0` ⇒ 退到 THP。
11-02 那几次 run 还有 `FileExpertSource: … 33.45 GiB page-locked cache complement … pinned 33.45 GiB in 117 s`
（另一条代码路径），11-03 13:01 起改走 arena + file cache。

**这条不追**：配 36,727 个 2 MiB 页要 71.7 GiB 预留，机器 125 GB 且已用 80 GB，物理上配不出；
而且当前 decode（79–80 tok/s）已高于 `W897` 基线的 70.7。**记为"已知状态"**（P255）。

### 7.6 处置

- 新容器已删，旧容器已恢复（`Ulimits []`、`ulimit -l 8192`、`VmLck 0`、available 45 GB），`/health ok`。
- `R67` 判 **DONE_NEG**：不是方法错，是**前提不成立**（内存够 ⇒ 无收益；内存不够 ⇒ 付不起代价）。
- **可复用的一条**：`--ulimit memlock=-1` 本身无害（参数验证过、容器参数逐字段一致），
  将来若上更大内存的机器（能同时容纳 PLE 26.8 + 专家 33.45 + 余量），这条应重测。
"""
p = "W920_PARAM_AUDIT.md"
io.open(p, "a", encoding="utf-8").write(add)
print("W920 §7 appended")

# ---- 2) R67 -> DONE_NEG ----
lines = io.open("PROGRESS.tsv", encoding="utf-8").read().split("\n")
done = False
for i, l in enumerate(lines):
    f = l.split("\t")
    if len(f) == 10 and f[1] == "R67":
        f[6] = "1"; f[7] = "DONE_NEG"
        f[8] += (" 【W920 §7 实测 2026-11-03 23:2x｜2 次重建/回滚，生产已恢复】**做成了但零收益**："
                 "重建容器加 `--ulimit memlock=-1` 后 `VmLck 28,125,140 kB`（=26.82 GiB，正好 PLE 大小）、"
                 "日志从 `PLE table loaded (not locked)` 变为 `PLE table locked in RAM ... in 1.7 s`。"
                 "**但** prefill 8.843→8.860 s（持平）、decode 稳定段 79.04→79.48（+0.6%，噪声内）、"
                 "宿主 available 43→18 GB。**根因：上游 6% 的前提是表被反复回收，我们内存够、页没被回收 ⇒ 未锁=已锁；"
                 "而锁定的 RAM 代价我们付不起（PLE 26.82 + 专家 arena 71.73 = 98.55 GiB / 125 GB）。** "
                 "**同时纠正我自己的错误归因**：专家 arena 的 `read through the file cache` 从 11-03 13:01 的 run 就开始了（行 106800），"
                 "早于本次实验 10 小时，两臂相同 ⇒ 冷启差异（69.64 vs 48.95）来自 cache 预热状态不同，不是 PLE 造成的。"
                 "**顺带发现**：`MAP_HUGETLB unavailable (needed 36727 2 MiB pages, vm.nr_hugepages=0)` ⇒ 专家 arena 走 THP；"
                 "配 36,727 页需 71.7 GiB 预留，物理上配不出，且当前 decode 79-80 已高于 W897 的 70.7 ⇒ 不追（P255）。"
                 "已回滚：`Ulimits []`、`ulimit -l 8192`、`VmLck 0`、available 45 GB、`/health ok`")
        lines[i] = "\t".join(f); done = True
        print("R67 -> DONE_NEG")
        break
assert done
io.open("PROGRESS.tsv", "w", encoding="utf-8").write("\n".join(lines))

# ---- 3) P255: hugepage 状态 ----
prow = ["P255", "HOST", "vm.nr_hugepages（专家 arena 的显式 hugepage）", "0（走 THP）",
        "memory", "REFERENCE", "-", "-", "P62",
        "W920 §7.5",
        "【W920 立 2026-11-03 23:2x】日志逐字：`expert arena: cudaHostRegister PORTABLE ok; "
        "MAP_HUGETLB unavailable (needed 36727 2 MiB pages, vm.nr_hugepages=0); transparent huge pages requested (MADV_HUGEPAGE)`。"
        "需 36,727 × 2 MiB = 71.7 GiB 预留；宿主 125 GB 且已用 80 GB ⇒ **物理上配不出**，不追。"
        "同时记录状态迁移：11-02 的 run 走 `FileExpertSource`（`33.45 GiB page-locked cache complement … pinned 33.45 GiB in 117 s`），"
        "11-03 13:01 起改走 `expert arena + file cache`；当前 decode 79-80 tok/s 高于 W897 基线 70.7 ⇒ **新状态不劣，保持**"]
plines = [l for l in io.open("params/PARAM_REGISTER.tsv", encoding="utf-8").read().split("\n") if l.strip()]
plines.append("\t".join(prow))
io.open("params/PARAM_REGISTER.tsv", "w", encoding="utf-8").write("\n".join(plines) + "\n")
print("P255 appended, cols =", len(prow))
