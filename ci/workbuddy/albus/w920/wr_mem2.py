import io, os
os.chdir(r"D:/workbuddy_space/strata_ws/.workbuddy/memory")
sec = """
## 23:2x W920 · arg/env 全量审计 + PLE mlock 实测（零收益，已回滚）
- **两个检测参数（`DECODE_TIMING`/`SPEC_DEPTH`）判保留**：计数无条件（`generate.cpp:17160-17166`/`:17099`），env 只控 `fprintf` ⇒ 撤了不省时间只丢唯一口径。日志里各 17,691 行 / 231 行，**每请求各 1 行**，代价每窗口 4 次 `Clock::now()`≈80–100 ns = 0.0002%。P248/P251 原本就是 CONFIRMED，本轮只是复核并量化。
- **找到一个真问题：`/data/strata-trace` 是 marker file，不是 env**（`generate.cpp:12194-12208`：`getenv(STRATA_TRACE) || filesystem::exists(/data/strata-trace) || exists(.strata-trace)`），`tr()` 每次调用重新 stat、每行 `fprintf`+`fflush`。现场 0 B 文件 mtime **11-01 18:42**，进程内无该 env ⇒ **任何 env 审计都看不见它**。后果：`strata trace:` **23,812 行 = 日志 22%**，`window` 类 17,908 行在 decode 热路径。**A-B-A 同进程零重启**：decode 78.29 / **80.21(off)** / 79.63，prefill 8.857/8.843/8.811 ⇒ 差 ≤2.45%、相邻 0.7%，**够不到 2×CV ⇒ 性能代价 <1% 测不出**，但噪音真。已 `mv` 成 `.off`；需要看 prompt 复用率（测 R68 时）`touch` 即开，零重启。记 **P254**。
- **PLE mlock（R67）= DONE_NEG**：重建容器（逐字段复现 bridge/ipc=host/shm 64m/video/label=disable/kfd+dri/两 bind/unless-stopped/7 env/同 Cmd）只加 `--ulimit memlock=-1` ⇒ `VmLck 28,125,140 kB`（=26.82 GiB）、日志 `PLE table locked in RAM ... 1.7 s`。**但零收益**：prefill 8.843→8.860（持平）、decode 稳定段 79.04→79.48（+0.6% 噪声内）、available 43→18 GB。**根因：上游 6% 的前提是表被反复回收，我们内存够、页没被回收 ⇒ 未锁=已锁；而锁定代价付不起（PLE 26.82 + 专家 arena 71.73 = 98.55 GiB / 125 GB）。已回滚（`Ulimits []`/`ulimit -l 8192`/`VmLck 0`/available 45 GB/health ok）。**
- **自我纠错（重要）**：我一度说"专家 arena 退化成 file cache 是 PLE 锁定的锅"——**错**。`expert arena read through the file cache` 从 **11-03 13:01 的 run 就开始了**（行 106800），早于实验 10 小时，两臂相同 ⇒ 冷启差异（69.64 vs 48.95）来自 cache 预热状态不同。**记住：下结论前先查"这个现象从哪一次 run 开始"。**
- **顺带发现 P255**：`MAP_HUGETLB unavailable (needed 36727 2 MiB pages, vm.nr_hugepages=0)` ⇒ 专家 arena 走 THP；36,727 页 = 71.7 GiB 预留，125 GB 机器已用 80 GB ⇒ 配不出，不追；且当前 decode 79–80 已高于 W897 的 70.7。状态迁移已记：11-02 走 `FileExpertSource`（33.45 GiB page-locked complement），11-03 13:01 起走 arena+file cache。
- **其余参数判定**：`HSA_OVERRIDE_GFX_VERSION=9.0.6` **冗余**（不设 `rocminfo` 原生报 `gfx906`，与 P11"不要改"一致）；`--vision` **有效**（698 次 `strata-vision: encoded`，22 线程只在加载期）；`--max-context 262144` **不预占显存**（KV 按需 `kv ensured`）；`--conversation-cache-mib 4096` **够用**（`parked=4`/1.18 GB，`evictions=20` 不增长）；rocblas tuning 文件在（5,576 B）。
- **方法论两条**：①**控制通道有三类**——env / argv / **文件探针**，审计要 grep `std::filesystem::exists|access(|stat(`；②**decode A/B 必须在 expert cache 饱和后测**（实测命中率 96.6→97.6% 仍在爬，同期 decode 69.6→80.7），否则把预热误判成收益。
- 产物：`deploy/W920_PARAM_AUDIT.md`；`PROGRESS.tsv` +R71(DONE) +R67(DONE_NEG)；`PARAM_REGISTER` +P254 +P255；`albus/w920/*.sh`。进度 **86/155 = 55.5%**，主线 **86/127 = 67.7%**。
"""
with io.open("2026-11-03.md", "a", encoding="utf-8") as f:
    f.write(sec)
print("ok", len(sec))
