import io, os
os.chdir(r"D:/workbuddy_space/strata_ws/.workbuddy/memory")
sec = """
## 22:4x W919 · 上游 release notes 逐条读：找到一条**现成的损失**（PLE 表从未锁进 RAM）
- **我上一轮错了**：说"0.2.8 起上游不写 release notes"——我只在仓库 `docs/` 里找（最后一份 0.2.7），而 **GitHub Releases 正文从不进仓库**。0.2.10 body **38,007 字节**、0.2.9 19,926、0.2.8 9,764。取法：`api.github.com/repos/Niko1221/Strata/releases?per_page=10` 的 `.body`，无截断。
- **gfx906 不在上游评测面上**：全部 10 个 release 里 `gfx906|MI50|Vega` 只出现 **1 次**（0.2.7 的 `--split-serve`，用户 @MarcoTool 的 RTX3070+两张 MI50 手工方案，且实测比 layer split 慢 16–48%）。各 release 提到的 AMD 架构全为 gfx1100/1151/1200/1201/1011/1030/1031（RDNA2/3/4）⇒ **上游的 AMD 面 = RDNA 面**。
- **【实证】PLE 表 26.8 GiB 一直没锁进 RAM**：0.2.10 `#4671` 原文点名 "the **26.8 GiB** mlock of the PLE table was refused … up to **6% slower decode**"，正是我们的表（W910 实测 26.82 GiB）。现场：日志每次 startup 都报 `PLE table mlock failed (Cannot allocate memory; raise ulimit -l)` + `PLE table loaded (not locked)`，`VmLck: 0 kB`；`ulimit -l`=8192 KiB，`/proc/<engine>/limits` soft=hard=8388608，`HostConfig.Ulimits=[]`，`systemctl show docker LimitMEMLOCK=8388608` ⇒ 容器内 hard 即 8 MiB，非 root 提不动。
- **最小验证（不碰生产，1 分钟）**：同镜像临时容器 `--ulimit memlock=-1` ⇒ `mlock(256 MiB) rc=0`；生产容器同调用 `rc=-1 errno=12`。**内存账成立**：`RAM budget 76 GiB` 已含 PLE 26.8 + 专家 33.45＝60.25 GiB；专家 cache 走 `pinned/mapped`（`mapped pinned cache complement ready: pinned 33.45 GiB … page-locked and mapped`，不计 VmLck），PLE 走 `mlock(2)` ⇒ **放开 memlock 只影响 PLE**。**执行必须重建容器**（`--ulimit` 不能 `docker update`），破坏性，待确认。
- **三条与架构无关且命中我们形状的 0.2.10 修复**：①`#4677`/`243fdb21` serve stop bound——**HIP only**，单请求投机 + park 的末窗口快照被截断，上游实测 4/16→0/16 回退、复用 98.36→99.74%，"about 6% of a 12K prompt read again"；我们形状全对上（HIP + --spec 4 + 单流 + CKPT_MOVE_PARK），树里 `STRATA_SERVE_STOP_BOUND` 命中 0。②`#4590`/`ed76b12f` penalty 按回复自身 token 计（我们是 Qwen，会改输出 ⇒ 需先过 W913 门）。③`#4741` BF16 projection→Q8_0（我们 581 个 BF16 张量但未触发，记档不立项）。
- **0.2.8/0.2.9 的 AMD 条目多数我们已有或架构不符**：`STRATA_WINDOW_MAX_T` 默认 `auto` = **HIP 16/CUDA 8**（`CMakeLists:102`）⇒ 0.2.8 的"16 行窗口"**我们早就有**；九个 parallel 设置（`CKPT_POOL`/`SLOT_CKPT_MOVE`/`QSA_SLOTS`…）树里都有但**单流不适用**；GDN tensor core / gfx12 chunked 被架构门挡住。DFlash2 支持列表（CUDA 8.6/8.9/12.0/12.1、gfx1100/1151/1201、Metal、Arc）**不含 gfx906**。
- **上游自述印证 W913**：0.2.9 已知问题「DeepSeek is not repeatable at temperature 0 … traced this to **the expert cache, which moves experts between the CPU and the GPU; the two round differently**；`--no-expert-cache` 后一致，但**单卡掉 58% decode**」，0.2.10 复述并加「we compared engines by **KL, not by identical tokens**；this was already so in 0.2.9」⇒ 我测的跨进程 0.0032 KL 有供应商背书的根因；**"钉死驻留"这条路被 58% 代价封死**，R60/R64 的精度门只能按 0.0032 表述。
- **账实不符（第二次）**：`W918` 当时说"队列改为 → R66 →"，但 `W832` 的执行顺序行里**从来没有 R66/R65**（只加了表行）。已在 W919 一并修正，并把新增四条写进顺序行。
- **队列**：`~~R59~~ → R67(PLE mlock,待确认) → R66 → R68(stop bound) → R61 → R60 → R58 → R63 → R64 → R69 → R70 → R65 → R49 → R50 → R30′ → M3`。进度 **84/154 = 54.5%**，主线 **84/126 = 66.7%**。
- 产物：`deploy/W919_RELEASE_NOTES_READ.md`；`PROGRESS.tsv` +R67/R68/R69/R70；`W832 §6.5` +4 行 + 修顺序。生产零改动（只读 + 一个 --rm 临时容器）。
"""
with io.open("2026-11-03.md", "a", encoding="utf-8") as f:
    f.write(sec)
print("ok", len(sec))
