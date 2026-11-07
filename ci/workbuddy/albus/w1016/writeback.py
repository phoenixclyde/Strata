import io

PLAN = "deploy/W832_OPT_PLAN_V2.md"
PROG = "deploy/PROGRESS.tsv"
BUNDLE = "ci/bundle_budget/BUNDLE.tsv"

BLOCK = '''
### 回写 · W1016（chunk 1024 一个臂，同时否掉我自己的三个机制假设）

机主令「继续」。队列首位是 R95，而 W1015 刚把 91 ms 的机制写成「复用等待（双缓冲可解）」。**这个机制没被测过**，
本轮用最小代价测它：同一个 2K prompt，把 `--prefill` 从 `auto:16384` 改成 `1024`，于是同一请求要过 **2 个 chunk**，
每层的 `d2h_sync`（`pinned_ring.hpp:105-114`，`cudaMemcpyAsync` + **`cudaStreamSynchronize`**）就跑 **96 次**而不是 48 次。

| 量 | chunk 16384（1 chunk） | chunk 1024（2 chunks） | 比值 |
|---|---:|---:|---:|
| prefill@2000 | **513.65 tok/s** | **406.07** | **−20.94%**（band 0.86） |
| TTFT | 4.096 s | 5.489 s | **+34.0%** |
| `host grouping` | 91 ms | 105–121（中位 **108**） | **×1.19** |
| `dequant` | 161 ms | 398–464 | ×2.6 |
| `wait copy` | 37 ms | 364–521 | **×10–14** |
| gemm gate/up | 816 | 1227–1267 | ×1.52 |
| gemm down | 510 | 764–802 | ×1.53 |

**三个模型全被否：**

1. **「每层一次 sync 的固定延迟」**：层-趟数翻倍，`host grouping` 只涨 19%（91→108），不是 ×2 ⇒ 否。
2. **「拷贝 3.2 MB」**：跨 chunk 拷贝量翻倍，也没翻倍 ⇒ 否（而且绝对值差 100 倍）。
3. **「建表随 T 增长」**：16K（T=16375）只有 **64 ms**，比 2K 的 91 ms **更小** ⇒ 否。

⇒ **`host grouping` 是「每请求约 90–110 ms」的量，与 chunk 数、token 数都弱相关。** 它不是同步延迟，也不是拷贝、
也不是直方图。**W1015 写的「复用等待、双缓冲可解」是错的机制，现撤回**（`P331 → DONE_NEG`）；归因必须靠 `P309` 的
两个事件（launch 前后量 `busy/phase`），在那之前不许写双缓冲代码。

**这个臂顺带把「为什么 chunk 必须是 16384」量化了**：切到 1024 后 `wait copy` ×10–14、`dequant` ×2.6、
GEMM ×1.5，合计 −20.94%。以前这条只是「日志里写着 auto:16384」，现在是 21 个点的代价。

**外网（归因手段）**：ROCm 侧测量同步阻塞时间有现成仪器——`rocprofiler-sdk` 的
`rocm_sync_nanoseconds`（按 HIP 同步 API 累计 host 阻塞时间，`hipDeviceSynchronize`/`hipStreamSynchronize`/…），
另有 `rocm_kernels_nanoseconds` / `rocm_memcpy_nanoseconds`。但该文档写明 **Requires ROCm 7+**，我们是 5.7/6.x +
`HSA_OVERRIDE_GFX_VERSION=9.0.6` ⇒ 该仪器在 166 上不可用。**结论：只能用树内事件（P309），不要指望外部 profiler。**
'''
s = io.open(PLAN, encoding="utf-8").read()
if "回写 · W1016" not in s:
    s = s.rstrip("\n") + "\n" + BLOCK
io.open(PLAN, "w", encoding="utf-8", newline="\n").write(s)

ROWS = [
 ("B6判定探针", "P332", "chunk 1024 实测 −20.94% / TTFT +34%：`auto:16384` 的正当性被定量证实", "W1016", "DONE",
  "**W1016 立**：同一 2K prompt 改 `--prefill 1024`（2 chunks）：prefill@2000 **513.65 → 406.07 tok/s（−20.94%）**、TTFT 4.096→5.489 s（+34.0%）；"
  "相位 `wait copy` 37→364–521 ms（×10–14）、`dequant` 161→398–464（×2.6）、gu 816→1227–1267（×1.52）、down 510→764–802（×1.53）。"
  "结论：砍 chunk = 让小批 GEMM 与每 chunk 的专家搬运全部失摊，21 个点。",
  "albus/w1016/chunk1k_raw.txt"),
 ("B6判定探针", "P333", "`host grouping` 三模型全否：不是每层 sync、不是拷贝、不随 T 增长 ⇒ 每请求 90–110 ms，归因待 P309", "W1016", "DONE_NEG",
  "**W1016 立**：chunk 翻倍（48→96 次 d2h_sync）时 `host grouping` 91→108 ms（×1.19，非 ×2）；16K（T=16375）只有 64 ms（比 2K 更小）；"
  "拷贝量 3.2 MB ≈ 0.5 ms 差两个数量级 ⇒ 三模型皆否。**撤回 W1015/P331 的「复用等待、双缓冲可解」**；归因必须先做 `P309` 事件实验（launch 前后量 busy/phase）。",
  "albus/w1016/chunk1k_raw.txt"),
]
lines = io.open(PROG, encoding="utf-8").read().split("\n")
hi = next(i for i, l in enumerate(lines) if not l.startswith("#") and l.count("\t") >= 9)
head = lines[hi].split("\t")
ID, ST, NOTE = head.index("id"), head.index("status"), head.index("note")
have = {l.split("\t")[ID] for l in lines if l.count("\t") >= 9}
add = ["\t".join([b, pid, item, src, "count", "1", "1", st, note, ref])
       for b, pid, item, src, st, note, ref in ROWS if pid not in have]

for i, l in enumerate(lines):
    if l.count("\t") < 9 or l.startswith("#"):
        continue
    c = l.split("\t")
    if c[ID] == "P331":
        c[ST] = "DONE_NEG"
        c[NOTE] = ("**W1016 否证（撤回）**：chunk 1024 让 `d2h_sync` 次数翻倍，`host grouping` 只 91→108 ms（×1.19），16K 更小（64 ms）⇒ "
                   "既不是每层 sync、也不是拷贝、也不随 T 增长。W1015 的「复用等待、双缓冲可解」撤回，归因待 `P333`/`P309`。") + " " + c[NOTE]
        lines[i] = "\t".join(c)
if add:
    while lines and lines[-1] == "":
        lines.pop()
    lines += add + [""]
io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(lines))

b = io.open(BUNDLE, encoding="utf-8").read()
b = b.replace("B1\tR95-plan\tgroup plan build moves to the issuer thread\thost grouping\t91\t-100.0\t4.0\testimate\tY\tCANDIDATE\tci/prefill_phases/PREFILL_PHASES.tsv",
              "B1\tR95-plan\thost grouping: per-request 90-110ms, mechanism UNLOCALIZED (needs P309)\thost grouping\t91\t-100.0\t4.0\testimate\tY\tCANDIDATE\talbus/w1016/chunk1k_raw.txt")
io.open(BUNDLE, "w", encoding="utf-8", newline="\n").write(b)
print("plan block + %d rows + P331 withdrawn" % len(add))
