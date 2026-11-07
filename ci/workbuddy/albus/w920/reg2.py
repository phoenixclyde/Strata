import io, os
os.chdir(r"D:/workbuddy_space/strata_ws/deploy")

row = ["P254", "MARKER", "/data/strata-trace（STRATA_TRACE 的文件形态）",
       "已关（改名 .off，需要时 touch 即开）", "measurement", "ADOPTED",
       "-", "-", "P168",
       "W920 §2",
       "【W920 立 2026-11-03 22:5x】**不是 env，是文件**。源码 `generate.cpp:12194-12208`：`trace_on()` = `getenv(STRATA_TRACE) != nullptr || std::filesystem::exists(/data/strata-trace) || std::filesystem::exists(.strata-trace)`，`tr()` 每次调用都重新 stat、每行 `fprintf(stderr)`+`fflush`。现场：`/data/strata-trace` 存在（0 B，mtime 2026-11-01 18:42），进程内**无** `STRATA_TRACE` env ⇒ 任何 env 审计都看不见它。后果：`strata trace:` **23,812 行**（占日志 22%），其中 `window` 类 **17,908 行**在 decode 窗口循环（`generate.cpp:17067`）。**A-B-A 实测（同进程零重启，唯一变量 marker）**：decode median A1(trace on, 冷启第一跑) 78.29 / **B(off) 80.21** / A2(on) 79.63，prefill 8.857/8.843/8.811 s ⇒ 差值 ≤2.45%、相邻 0.7%，**够不到 2×CV ⇒ 性能代价 <1%，测不出来**；22% 的日志噪音是真的。**处置**：`mv /data/strata-trace /data/strata-trace.off`，需要看 prompt 复用率时 `touch /data/strata-trace` 零重启即开（这正是作者设计意图：a file lets tracing be turned on and off on a live service instead of costing a restart per experiment）。**教训**：参数审计必须包含文件探针，见 W920 §4"]

p = "params/PARAM_REGISTER.tsv"
lines = [l for l in io.open(p, encoding="utf-8").read().split("\n") if l.strip()]
lines.append("\t".join(row))
io.open(p, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("P254 appended, cols =", len(row))

r71 = ["B10环境与版本", "R71",
       "引擎 arg/env 全量审计（18 flag/33 元素 + 18 项生效 env）：找 设了没用 / 该撤没撤 / 有代价 的项",
       "W920 §0-§3", "count", "1", "1", "DONE",
       "**W920 实测（2026-11-03 22:5x，零停服）**：①**两个检测参数（DECODE_TIMING / SPEC_DEPTH）判保留**——计数无条件（generate.cpp:17160-17166 / :17099），env 只控 fprintf，撤了不省时间只丢唯一口径（17,691 行 + 231 行，每请求各 1 行，代价每窗口 4 次 Clock::now≈80-100 ns = 0.0002%）。②**找到一个真问题**：/data/strata-trace **marker file**（非 env）常开两天 ⇒ strata trace: 23,812 行占日志 22%，window 类 17,908 行在 decode 热路径，每次 tr() 2 次 stat + 1 次 fflush；**A-B-A 同进程零重启** decode 78.29/80.21/79.63 ⇒ 性能代价 <1% 测不出，但噪音真；已 mv 成 .off，需要时 touch 即开（P254）。③**HSA_OVERRIDE_GFX_VERSION=9.0.6 冗余**：不设它 rocminfo 原生报 gfx906，与 P11 的不要改一致，登记为非调参项。④**--vision 有效**（698 次 strata-vision: encoded，22 线程只在加载期）。⑤**--max-context 262144 不预占显存**（KV 按需 kv ensured）；**--conversation-cache-mib 4096 够用**（parked=4 / 1.18 GB，evictions=20 不增长）；**rocblas tuning 文件存在**（5,576 B）。⑥**方法论**：控制通道有三类——env / argv / **文件探针**，审计必须 grep std::filesystem::exists 与 access( 与 stat(。⑦**新纪律**：decode expert cache 命中率 96.6→97.6% 仍在爬 ⇒ **任何 decode A/B 必须在 cache 饱和后测**，否则把预热误判成收益",
       "W920;W915"]

with io.open("PROGRESS.tsv", "a", encoding="utf-8", newline="") as f:
    assert len(r71) == 10
    f.write("\t".join(r71) + "\n")
print("R71 appended")
