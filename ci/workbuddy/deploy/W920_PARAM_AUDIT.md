# W920 · 引擎 arg/env 全量审计：两个检测参数怎么处置，以及一个藏在文件里的开关

日期：2026-11-03 22:5x
状态：发现并处置 1 项（trace marker）；1 项判为冗余；其余无问题；PLE mlock 待执行

---

## 0 审计对象的真实清单（从 `/proc/<pid>` 取，不凭记忆）

**arg：18 个 flag / 33 个数组元素**

```
--serve | --pack /data/packs/ud-q4_k_xl | --native …UD-Q4_K_XL-00001-of-00004.gguf
--expert-profile /src/data/expert-profile.bin | --expert-cache auto | --pcie-frac 0.20
--spec 4 | --spec-min-p 0.70 | --mtp /data/mtp/rt | --max-context 262144 | --kv k8v4
--prefill auto | --prompt-cache-every 8192 | --expert-profile-save /data/profiles/q4kxl-learned.bin
--conversation-cache-mib 4096 | --vision | --mtp-window 8192 | --vram-reserve-mib 832
```

**env：config 9 项（`/proc/environ` 可见）+ tuned 展开 7 项 + 默认 2 项 = 18 项生效**

| 类别 | 项 |
|---|---|
| config 9 | `HSA_OVERRIDE_GFX_VERSION=9.0.6`、`STRATA_CKPT_MOVE_PARK=1`、`STRATA_DECODE_TIMING=1`、`STRATA_GFX906_TUNED=1`、`STRATA_PREFILL_CPU_SHARE=auto`、`STRATA_PREFILL_CPU_SHARE_MAX=3072`、`STRATA_RESIDENT_HEADROOM_GIB=0.5`、`STRATA_ROCBLAS_TUNING=…5.7.0.txt`、`STRATA_SPEC_DEPTH=1` |
| tuned 7 | `ATTN_QUERY_SWIZZLE` / `GDN_PP` / `HC_Q8` / `SELECT_SIMT` / `ROUTE_TAIL_SKIP` / `MMQ_KQ` / `HIP_PROMPT_F16` |
| 默认 2 | `GDN_HEAD` / `GFX906_ATTN_REDUCE12` |

---

## 1 两个检测参数（`DECODE_TIMING` / `SPEC_DEPTH`）：**保留，不撤**

### 1.1 它们各自做什么、打多少行

| env | 输出（每请求 1 行） | 日志累计 |
|---|---|---|
| `STRATA_DECODE_TIMING=1` | `strata decode timing: 4 windows, avg T 2.50, 2.00 tokens/window, 49.33 ms/window = adapt wait 0.02 + verify 41.19 (GPU-reach wait 24.88 + …)` | **17,691 行** |
| `STRATA_SPEC_DEPTH=1` | `strata serve: spec depth: accepted/tested 3/3 2/2 1/1 0/0 0/0` | 231 行 |

### 1.2 代价：**关 env 不会变快，只有删代码才行**

`W915` 已核过源码：计数**无条件**执行（`generate.cpp:17160-17166` 的 `dt_run += msd(tw0,tw1)`、`:17099` 的 `++dp_tested[d]`），
env 只控制 `fprintf`（`:16805/:17229`、`:17735`）。所以：

- 撤掉 env ⇒ 只丢观测，**不省时间**；
- 留下的代价 = 每窗口 4 次 `Clock::now()` ≈ 80–100 ns，对 48 ms 窗口是 **0.0002%**。

### 1.3 结论：**保留**

它们是 decode 窗口预算与 MTP 按深度接受率的**唯一口径**（`W873` 起所有窗口 ms 都来自前者；
后者是 `--spec 4` 是否划算的唯一直接读数）。**撤了等于自断眼睛，换不来速度。**

要减噪音不该撤 env，而该像作者那样做成"文件开关"（见 §2）——但那是改代码，收益 <0.01%，**不做**。

---

## 2 找到一个真问题：`/data/strata-trace` 这个 **marker file** 常开了两天

### 2.1 它不是 env，所以任何 env 审计都看不见

源码 `generate.cpp:12194-12208`：

```cpp
// STRATA_TRACE=1, or a marker file (stat'ed once per request): the container's environment is
// fixed at create time, so a file lets tracing be turned on and off on a live service instead of
// costing a restart per experiment.
const auto trace_on = [] {
    if (std::getenv("STRATA_TRACE") != nullptr) return true;
    std::error_code ec;
    return std::filesystem::exists("/data/strata-trace", ec) ||
           std::filesystem::exists(".strata-trace", ec);
};
auto tr = [&](const char* what, ...) {
    if (!trace_on()) return;                     // ← 每次调用都 stat 两个路径
    ...
    std::fprintf(stderr, "strata trace: %s %lld %lld %.1f ms\n", ...);
    std::fflush(stderr);                         // ← 每行强制 flush
};
```

现场：**`/data/strata-trace` 存在，0 字节，mtime `2026-11-01 18:42:19`**，而进程里**没有** `STRATA_TRACE` env。

### 2.2 它造成了什么

| 项 | 数值 |
|---|---|
| `strata trace:` 总行数 | **23,812**（占日志 22%） |
| 其中 `window` 类 | **17,908 行**（decode 窗口循环里，`generate.cpp:17067` 的 `tr("window", p, T)`） |
| 每次 `tr()` 的系统调用 | 2 次 `stat`（两个路径）+ 1 次 `write`（`fflush`） |
| 累计 | ≈ 4.8 万次 `stat` + 2.4 万次无缓冲 `write` |

### 2.3 A-B-A 实测：**性能代价测不出来**

同进程、零重启，唯一变量是 marker 是否存在（`bench_pair --prefill-words 4100 --n 6 --decode-tokens 256`）：

| 臂 | marker | decode median | 去冷启 median | prefill median |
|---|---|---|---|---|
| A1 | 有 | 78.29 | 78.87 | 8.857 s（3 次真 prefill） |
| **B** | **无** | **80.21** | 80.21 | 8.843 s（6 次） |
| A2 | 有 | 79.63 | 79.75 | 8.811 s（6 次） |

`A1 < A2 < B`，最大差 2.45%、相邻差 0.7%，**够不到 2×CV**（A1 是被冷启压低的第一次跑）。
⇒ **结论：trace 的性能代价 <1%，测不出来；但 22% 的日志噪音是真的。**

### 2.4 处置：已关，但保留开关能力

```bash
docker exec strata166-407 mv /data/strata-trace /data/strata-trace.off
# 需要时：docker exec strata166-407 touch /data/strata-trace   （零重启生效）
```

**这是能力不是 bug**——作者就是为"不重启做实验"设计的。问题只是它被遗留在"开"状态两天。
后面测 `R68`（stop bound 的 prompt 复用率）时，正好需要它输出 `prompt N tokens (M reused)`，届时 `touch` 即开。

---

## 3 其余参数逐条判定

| 参数 | 判定 | 依据 |
|---|---|---|
| `HSA_OVERRIDE_GFX_VERSION=9.0.6` | **冗余，但无害，暂留** | 不设它 `rocminfo` 原生就报 `gfx906` / `amdgcn-amd-amdhsa--gfx906:sramecc+:xnack-`。gfx906 的覆盖值本来就是 9.0.6 ⇒ 设了等于没设。留着的唯一理由是"某些库会读这个变量做保守判断"，撤它需要一次整机 A/B，收益不明 |
| `--vision` | **有效，保留** | 日志有 **698 次** `strata-vision: encoded`，模型真的在吃图；加载 2.7–2.9 s 属启动成本。CPU 22 线程是**加载期临时**，运行期线程表里没有 vision 线程（29 个线程 = 4 stage + 2 main + watchdog + stdin + pool-2…21） |
| `--max-context 262144` | **不预占显存，保留** | KV 按需增长（日志只有 `kv ensured`，没有整池预分配）。显存账是 `expert cache 7463 slots / 21.79 GiB` + `prompt path 借 1578 slots / 4.62 GiB` + `MTP 1089 MiB` + `HC_Q8 0.63 GiB` + `剩 920 MiB` |
| `--conversation-cache-mib 4096` | **够用，保留** | `parked=4 bytes=1.18 GB`（上限 4 GiB），`evictions=20` 停在 20 不再增长 ⇒ 没满、没抖 |
| `STRATA_ROCBLAS_TUNING=…5.7.0.txt` | **有效** | 文件存在（5,576 B，10-31），内容是 prompt 路径 FP16-out GEMM 的 solution indices |
| `--mtp-window 8192` 与 `--prompt-cache-every 8192` 同值 | **不冲突，保留** | 一个管 MTP 草稿窗口、一个管 prompt 缓存落盘粒度，语义不同，同值是巧合 |
| `--pcie-frac 0.20` / `--vram-reserve-mib 832` / `--spec 4` / `--spec-min-p 0.70` | **有证据支撑，保留** | `P` 系列登记册已收口；`832` 对应日志 `832 MiB reserved (+281 draft head, +256 after)` |
| `STRATA_PREFILL_CPU_SHARE=auto` + `_MAX=3072` | **有效** | 日志 `prefill: the CPU share is ON by default for prompt chunks below 1024 tokens` |
| `STRATA_RESIDENT_HEADROOM_GIB=0.5` | **有效** | 对应 `RAM budget 76.00 GiB` 的余量 |
| `STRATA_CKPT_MOVE_PARK=1` | **有效** | 日志 `conversation cache: parked 221 tokens in 102.3 ms` |
| tuned 7 项 + 默认 2 项 | **已在各自条目收口** | `W913` §6、`W914` 逐项 KL 代价 |

---

## 4 一个方法论收获：控制通道不止 env

这次审计暴露的盲区：**我一直在 env 和 arg 里找参数，而作者留了第三个通道——文件。**

```
env      → 创建容器时固定，改一次要重启
arg      → 同上
marker   → 零重启，live 生效（这个 trace 开关就是）
```

⇒ 以后做"参数有没有问题"的审计，必须把**代码里所有能改变行为的输入**列全：
`getenv()` / `argv` / config json / **`std::filesystem::exists()` 这类文件探针** / 编译期默认值。

审计命令（可直接复用）：

```bash
# 找出所有"文件探针"式开关
grep -rn "std::filesystem::exists\|access(\|stat(" --include=*.cpp --include=*.cu src/ | grep -iE "trace|marker|enable|\.strata"
```

---

## 5 顺带记一条实验纪律（本轮实测发现）

`strata serve: decode expert cache hit rate` 在连续请求中 **96.6% → 97.6% 持续上升**，同期 decode 从 69.6 → 80.7 tok/s。
⇒ **任何 decode A/B 都必须在 agent cache 饱和后测**；否则"刚重启就跑"会系统性低估基线，
把 cache 预热误判成改动收益。这与 `W913` 的"重启丢前 2 请求"是同一条纪律的两个面。

---

## 6 复现命令

```bash
# 真实 arg / env
docker exec strata166-407 sh -c 'P=$(pgrep -f "strata-0.1.55t --serve"|head -1); tr "\0" "\n" < /proc/$P/cmdline'
docker exec strata166-407 sh -c 'P=$(pgrep -f "strata-0.1.55t --serve"|head -1); tr "\0" "\n" < /proc/$P/environ'

# marker 是否开着
docker exec strata166-407 ls -la /data/strata-trace /src/.strata-trace

# trace 行数占比
docker exec strata166-407 sh -c 'grep -c "strata trace:" /data/strata-huihui-ud-iq4_xs.log'
```


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
docker run -d --name strata166-407 --restart unless-stopped --network bridge -p 8090:8090 \
  --ipc host --device /dev/kfd --device /dev/dri --group-add video \
  --security-opt label=disable --shm-size 64m --ulimit memlock=-1 \
  -v /models:/models:ro -v /home/albus/strata166/data:/data \
  strata-gfx906:0.2.9-101 \
  bash -lc 'cd /src && exec python3 serve/server.py --engine strata --config /data/strata-huihui-ud-iq4_xs.json --port 8090'
```
