# W849 · 生产＝分支顶端（可复核），并结掉两条队列

> **【角色声明 · R44，2026-11-02 02:1x】本文 §5「下一步」是 2026-10-31 的队列快照，**不是队列本身**。**
> 本项目唯一排序处是 `W832_OPT_PLAN_V2.md §6.5`；两者若不一致，以 W832 为准。
> （`plan_lint` 的 E 项从本轮起把 `*QUEUE*` 也纳入检查，本文是被它抓到的。）

> 2026-10-31 20:57–21:10。机主令：「务必确保我在咱们的分支顶端。」
> 做法不是口头保证，而是**做了逐文件比对并固化成一条命令**；顺带把队列里 R2、X1 用现场数据结掉。

---

## 1 「在分支顶端」是怎么被证明的

### 1.1 结论：**是**

```
branch                 gfx906/0.2.9-mi50
HEAD                   aef9d256077a
HEAD tree              4ce087ba3ac2969ecf8eabd62b2a4f1c3e1be5d0
upstream/main          c62d5e3a  (v0.2.9)
upstream ahead/behind  0	1          ← 上游 0，我们领先 1 个提交
origin ahead/behind    0	0          ← 本地与 phoenixclyde 完全一致
dirty                  0
```

上游 side：GitHub API 直查 `Niko1221/Strata` `main` = **`c62d5e3a15`**、committer date `2026-10-31T02:23:01Z`，
与本地 `upstream/main` **同一个 commit**；tag `v0.2.9` 也指它 ⇒ **上游没有前进，我们就在它上面那一个提交上**。

### 1.2 关键证据：`/src` 与 HEAD 树**逐文件逐位相同**

不是抽样，是**全部 5319 个 git 跟踪文件**：

| 项 | 值 |
|---|---|
| `git ls-files` | **5319** |
| 生产容器 `/src` 里对应路径（python hashlib 逐个算 md5） | **5319**（缺失 0） |
| 两边 md5 相同 | **5319** |
| 不同 | **0** |
| 缺失 | **0** |

⇒ 镜像里那棵 `/src` 就是 `aef9d256` 的树，不是"接近"。

### 1.3 引擎二进制也来自这棵树

| 项 | 值 |
|---|---|
| 部署 `/data/bin/strata-0.1.55g` | `29b15bb4418bf15a…` |
| 构建产物 `gfx029-build/strata` | `29b15bb4418bf15a…` |
| 构建时间 / 提交时间 | 19:06 / 19:44（构建后这 12 个补丁文件再未改动：`git diff HEAD` = 0 行） |

### 1.4 固化成一条命令：`~/strata166/tmp/verify_tip.sh`

六项检查，全过才打印 `TIP-OK`，否则 `TIP-FAIL` 且退出码 1：

1. 分支 / HEAD / HEAD tree / upstream / ahead-behind；
2. 工作区 `dirty == 0`；
3. 与 `origin/<branch>` 一致（0/0）；
4. **`/src` 逐文件 md5 == HEAD 树**（5319 文件，全量）；
5. 引擎二进制 == 构建产物；
6. 门禁 `verify_patches.sh`。

实跑结果：

```
TIP-OK  生产 = 分支顶端（gfx906/0.2.9-mi50 @ aef9d256）   exit=0
```

已写进 `SESSION_STATE §7` 的汇报口径表；`PROD_BASELINE.tsv` 也补了 `commit / branch / tree / upstream` 四行，
以后每轮可以直接 diff。

> 注意一个**方法坑**（已修）：`docker exec … python3 - <<PY` 不带 `-i` 时 **stdin 不接入**，脚本读到空输入、输出 0 行，
> 看起来像"镜像里没有文件"。改成把脚本落到 `/data`（容器内可见）再 `docker exec python3 /data/xxx.py` 才可靠。第一次跑就踩了。

---

## 2 结掉 R2（`--vram-reserve-mib 1536`）：**前提不成立**

上游 #4781 的因果是"auto cache 太小 ⇒ prompt 掉速"。我们的现场：

| 证据 | 值 |
|---|---|
| 专家缓存槽位 | **7463**，且启动日志 `pre-filled 7463 of 7463 slots from the profile in 1.8 s` ⇒ **全部专家都在显存里** |
| 策略 | `PROFILE, ranked by routing frequency, **no eviction**` |
| 会话缓存淘汰 | `cc.evictions = 0` |
| PCIe 读量 | `hardware.gpu_pcie_rx_mb` **60 个样本恒 0.01 MB**（最大 0.02） |
| 每请求 PCIe 占比 | `pcie_share` 0.000 / 0.000 / 0.000 / 0.004 |

⇒ 没有淘汰、没有读盘、没有"cache 太小"这件事。**加大 reserve 只会把缓存做小**（每 704 MiB ≈ −230 槽）。
判定 **NA（前提不成立）**，不再占停服窗口。`W832 §6.5` 队列第 1 序同步划掉。

---

## 3 结掉 X1（`--ple-io ram`）：**引擎早就默认这么做了**

W814 量到 `--ple-io ram` 比 direct 快 8–23%，一直挂在"从未进生产"。现场日志：

```
strata generate: --ple-io ram chosen by the residency policy (the table is 26.8 GiB,
                 the expert arena still to fill 71.7 GiB and 118.9 GiB of RAM is available;
                 （实测同一行逐次启动在 118.7–118.9 GiB 之间浮动，AUDIT16 P3-24）
                 STRATA_PLE_AUTO_RAM=0 keeps the direct reads, --ple-io direct forces them)
strata generate: PLE table loaded (not locked) (--ple-io ram chosen by the residency policy) in 0.2 s
```

即 **0.2.7 起引擎自己按"内存够不够"选 `ram`**，我们早就在吃这个收益（这不是我们打开的，是默认）。
⇒ X1 记为 **NA / 已被上游默认行为取代**，不需要任何改动。

### 顺带说明 X2（`--ulimit memlock=-1`）为什么不值得现在花停服

启动横幅里有两行：

```
strata: PLE table mlock failed (Cannot allocate memory; raise `ulimit -l`): its pages stay faulted in but may be reclaimed
```

容器 `ulimit -l = 8192`（8 MB），而表是 **26.8 GiB** ⇒ 锁不住。但：

- 宿主/容器内存 **125 GB，available 45 GB**，表已在 RAM 里且已 pre-touch；
- 未 mlock 的后果只是"内存压力下可能被回收"，回收后重读是**从 RAM/buff/cache 再来**，不是回 SSD；
- 真要锁，得让容器 `--ulimit memlock=-1` 并重开容器（≈4 min 停服），**预期收益 0**（没有证据表明发生过回收）。

⇒ 按项目纪律（<3% 不采纳、不为卫生付停服）**降级为"内存紧张时再考虑"**，不占窗口。

---

## 4 本轮对生产：**0 落产**

只动了文档/账本与一个**检查脚本**（`verify_tip.sh`，不碰生产进程）。
生产仍是 `0.2.9t2` / 容器 `52a5d5c7b587` / `started 12:46:00Z` / `restarts=0` / `slots=7463 vram_free=920 pcie=0.20` / 门禁 PASS。

## 5 下一步（队列现在剩什么）

| 序 | 项 | 状态 |
|---|---|---|
| 1 | ~~R2 `--vram-reserve-mib 1536`~~ | **NA（W849，前提不成立）** |
| 2 | ~~X1 `--ple-io ram`~~ | **NA（W849，上游默认已做）** |
| 3 | **X15 ROCm 10.1.0 / HIP 7.16** | OPEN；零风险部分＝造候选镜像验加载，正式判定要停服 A/B + 重 tune rocBLAS 表 |
| 4 | R6 roofline 三条（LDS / DPP / dot2） | OPEN，不停服 ~40 min，决定 G8–G10 值不值得做 |
| 5 | M5 `STRATA_PREFILL_TIMING` 拆 TTFT | OPEN，需重启（env） |
| 6 | R3 移植 #3987（decode top-k split，端到端 +4.2%） | OPEN，要移植 + 停服 A/B |

**建议下一枪**：先做 X15 的零风险段（造 10.1 候选镜像、验 `ldd`/加载/`rocBLAS 识别 gfx906`），
再把停服窗口一次性用于「10.1 A/B + 视结果重 tune rocBLAS 表」——因为 rocBLAS 表换版本就作废，这窗口躲不掉。

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

