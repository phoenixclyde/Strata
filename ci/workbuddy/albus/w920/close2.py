import io, os
os.chdir(r"D:/workbuddy_space/strata_ws/deploy")

# ---- 1) W920 追加严格复测与机主决定 ----
add = """

---

## 8 复测（严格版）与机主决定：**保留 `--ulimit memlock=-1`**

§7 的第一版测量被冷启混淆（两臂 cache 状态不同）。按 §5 的新纪律重做：**两臂都先预热、再取 rep6-9 的 median**。

| 臂 | decode rep6-9 | median | prefill median | available |
|---|---|---|---|---|
| 未锁（`Ulimits []`） | 80.53 / 78.66 / 79.42 / 79.05 | **79.24** | 8.845 s | 43 GB |
| **已锁（`memlock=-1`）** | 80.01 / 80.66 / 78.84 / 78.58 | **79.43** | 8.826 s | 18 GB |

差值 **+0.24%（decode）/ +0.2%（prefill）**，远低于 2×CV ⇒ **实验结论：零收益**（与 §7 一致）。

**机主决定：保留**（2026-11-03 23:1x 原话「用。」）。理由与实验结论分开记：
- 实验层：本机内存充裕、PLE 页未被回收 ⇒ 锁定与不锁定在稳定期等价，**收益为 0**；
- 决策层：锁定是**预防性**的——长时间运行 / 内存压力变化时，未锁的页可能被回收，届时会掉到
  「可回收表」状态而不自知（日志只在启动时说一次）。锁住后这个风险不存在。
- 代价已知且可承受：`available 43 → 18 GB`（`PLE 26.82 + 专家 arena 71.73 + 会话缓存 4 + 权重 3.6 ≈ 106 GiB / 125 GB`）。

⇒ `R67` 的实验记录保持 **DONE_NEG**（结论：无性能收益），
配置决定另立 **P256**（`ADOPTED`，理由写明"预防性，非性能"）。**两者不能混：把零收益的实验写成"采纳有收益"就是造假。**

```bash
# 采用的容器参数（其余字段与 W920 §0 逐字段一致）
docker run -d --name strata166-407 --restart unless-stopped --network bridge -p 8090:8090 \\
  --ipc host --device /dev/kfd --device /dev/dri --group-add video \\
  --security-opt label=disable --shm-size 64m --ulimit memlock=-1 \\
  -v /models:/models:ro -v /home/albus/strata166/data:/data \\
  strata-gfx906:0.2.9-101 \\
  bash -lc 'cd /src && exec python3 serve/server.py --engine strata --config /data/strata-huihui-ud-iq4_xs.json --port 8090'
```
"""
io.open("W920_PARAM_AUDIT.md", "a", encoding="utf-8").write(add)
print("W920 §8 appended")

# ---- 2) P256：容器 memlock（配置决定，与 R67 的实验结论分开） ----
prow = ["P256", "HOST", "容器 --ulimit memlock=-1（PLE 表 26.82 GiB 锁进 RAM）",
        "已采用（2026-11-03 23:1x）", "memory", "ADOPTED", "-", "-", "P254",
        "W920 §7-§8",
        "【W920 立 2026-11-03 23:2x】**实验结论 = 零收益，配置决定 = 保留，两者分开记**。"
        "实测（两臂都预热后取 rep6-9 median）：未锁 decode **79.24** / 已锁 **79.43** = **+0.24%**，"
        "prefill 8.845 → 8.826 s = +0.2%，**远低于 2×CV ⇒ 无性能收益**；上游 0.2.10 `#4671` 的 6% 前提是"
        "「表被反复回收」，我们 available 43 GB、页未被回收 ⇒ 未锁=已锁。"
        "**保留理由是预防性**：长时间运行或内存压力变化时未锁的页可能被回收，届时日志只在启动时说一次、运行期不自知。"
        "代价：available 43 → 18 GB（PLE 26.82 + 专家 arena 71.73 + 会话缓存 4 + 权重 3.6 ≈ 106 GiB / 125 GB）。"
        "验证：`VmLck 28,125,140 kB`（=26.82 GiB）、`ulimit -l unlimited`、日志 `PLE table locked in RAM … in 1.8 s`。"
        "**回滚法**：把容器 `--ulimit memlock=-1` 去掉重建即可（旧容器对象保留在 `strata166-407.pre-w920b`）"]
plines = [l for l in io.open("params/PARAM_REGISTER.tsv", encoding="utf-8").read().split("\n") if l.strip()]
plines.append("\t".join(prow))
io.open("params/PARAM_REGISTER.tsv", "w", encoding="utf-8").write("\n".join(plines) + "\n")
print("P256 appended, cols =", len(prow))

# ---- 3) R67 备注补"机主决定保留" ----
lines = io.open("PROGRESS.tsv", encoding="utf-8").read().split("\n")
for i, l in enumerate(lines):
    f = l.split("\t")
    if len(f) == 10 and f[1] == "R67":
        f[8] += (" 【W920 §8 复测 + 机主决定 2026-11-03 23:2x】严格复测（两臂都预热、取 rep6-9 median）："
                 "未锁 79.24 / 已锁 79.43 = **+0.24%**，prefill +0.2% ⇒ **结论仍是零收益（DONE_NEG 不变）**。"
                 "**机主决定保留**（原话「用。」），理由是**预防性**（长时间运行/内存压力变化时未锁页可能被回收而运行期不自知），"
                 "非性能 ⇒ 配置决定另立 **P256**。代价：available 43→18 GB。"
                 "**纪律**：实验结论与配置决定必须分开记，把零收益写成「采纳有收益」即造假")
        lines[i] = "\t".join(f)
        print("R67 note appended")
        break
io.open("PROGRESS.tsv", "w", encoding="utf-8").write("\n".join(lines))
