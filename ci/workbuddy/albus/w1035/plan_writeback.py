#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1035：把本轮结论写进 W832 §6.5（并补 W1028–W1034 的指针块），再更新 §6.5.0 目录。

机主：「哪些在权威调优方案，哪些不在，你不在方案里的后面不就丢掉了？」
查证结果：方案里最后一个回写块是 W1027，W1028–W1035 八轮无块 ⇒ 结论只活在各自 reply.md。
"""
import io
import os
import re
import shutil
import sys

PLAN = "deploy/W832_OPT_PLAN_V2.md"
ROOT = "albus"

BLOCK_1035 = """
### 回写 · W1035（P392 重估：补丁不改 tile；decode 不稳的归因；收工仪式改成推式）

> 2026-11-07 02:2x–03:2x。生产零改动（0 重启 / 0 停机 / 0 回滚）。账本 `P407` / `P408` / `P410`。
> **本块是 W1028 之后第一个回写块**——那 8 轮的结论只活在各自 `reply.md`，见下一块的指针表。

**一、`P392`：要测的东西被证伪，不是「测不出」而是「测了也白测」。**

| 事实 | 证据 |
|---|---|
| 生产树是 `#29953` 的 **pre-fix** | `mmq.cuh:372` 仍是 `ggml_cuda_mmq_get_J_max()`（`min(ne11,512)` 向下走 8）；`mmq.cu:137` 与 `mmq.cu:206` 仍用它算 `src1_q8_1` 的 padding；`mmq_args` 末字段仍是 `int64_t ncols_opt`。与上游 PR（`3070d927`）的 `-` 块逐字对上 |
| 补丁**不改被选中的 tile** | 补丁删掉的 J 循环与本树 `mmq.cuh:1479-1500` 逐字相同；`ncols_opt`（dense `ne1≡ne11`、MoE 都是 `ne12`）与 `fallback`（`ne01%128!=0` ≡ `needs_fallback`）前后等价 ⇒ 同一个 `launch_mul_mat_q<type,J,fallback>` 实例 ⇒ 浮点累加顺序不变 |
| 我们热路径**本来就不越界** | `moe_mmq.cu:407` 的 `q8_bytes()` = `rows×pad512(cols)×… + 128×sizeof(block_q8_1_mmq)`，**固定 128 块余量 = 可能的最大 J**；`gemm.cu:1282` / `prefill.cpp:1605` 都走它 |
| 残余暴露（`mmq_pad_check.py`，250 条 gfx906 配置表） | Q4_K/Q5_K/Q6_K/Q5_1 最大 J=**64**、Q8_0=**128**；ggml dense 最坏 **16 块=2304 B**（仅 `ne11%8≠0`）；MoE `ids`（`prefill.cpp:1832`，`T*K` 无余量）**≤252 B**；真实形状 `ne11=1000/16384` 全部 `J_max==J_best` |
| **推论** | 数值面**按构造不变**；但这是源码等价，**不是运行期实测** ⇒ `P392` 按纪律**仍记 OPEN** |

**二、`-001` vs `-010` 测不出单条补丁（方法学，第二次同类错误）。**
`-010` = 「0.9.0 树 + mmq 头 @4c1004c」的**混合树**，两臂差的是一整棵树。KL 为 0 不能证明 `#29953` 无害，不为 0 也归因不到它。
⇒ **规矩**：单补丁归因必须「同树 + 单 patch」；混合树只能记「整栈」。同 `P389`（ladder-5 崩溃来自混合树）第二次出现。

**三、C 门（三臂、全词表 prefill logits）已备跑，未执行。**
`001` / `001b`（同 exe 新容器=自一致地板）/ `010`；每臂 `quant_quality.py prompt`：5 段 × 4 前缀长度 = **20 个配对点、全词表 float32 logits**，走批量 prefill（工具自己删 `--short-read`），避开上次 64 W 空转的 decode 窗口路径。命令行由镜像内 `engine_args()` 算出并逐字比对，三臂只差 exe 与 profile 落盘路径。安全：每臂一次性容器 + 停服后断言 `engines=0` 且 VRAM<2 GB + 单臂 270 s `timeout` + 720 s guard + 任一臂失败即中止。偏差（三臂相同）：`--kv fp16`、`CPU_SHARE=0`、`--expert-cache 1500`、`--max-context 1512`。**需停机 10–14 min，等机主点头。**

**四、decode 不稳：主因是专家缓存命中率，不是线程数。**

| 分桶（106 个 ≥64 token 请求，取自引擎日志） | n | decode 均值 |
|---|---|---|
| expert cache 命中 **<90%** | 28 | **51.3 tok/s** |
| 命中 **≥90%** | 78 | **65.0 tok/s** |

`corr(命中率, tok/s)=0.49`；全体 CV **21.1%**（39.5–82.2）；同一请求连跑 5 次 CV **17.6%**。VRAM 只装 7463 个专家、全包约 12288 个，未命中那部分正是 CPU 池算的 ⇒ **线程数放大每次未命中的代价**。
**`P265` 的证据缺口**：它的 decode 臂是 20 workers 36.23 vs 10 workers 36.53，**2×CV 带宽 13.4%**，且 bench 用同一条提示反复打（命中率趋近 100%）⇒ 未命中路径未被走到。**20 vs 10 的冷请求 A/B 未做，需一次重启。**

**五、磁盘读的归因（一轮内修正三次，最终版）。**
不是 PLE、不是 `P254`。请求前后对同一进程 `smaps` 逐映射取 Rss 差：读 **34.45 MB** 的那次，Rss 增量 **32.9 MiB 全部落在** `…-00002-of-00004.gguf`，`rchar` 仅 0.02 MB ⇒ **mmap 缺页**。
- 该 shard **49.86 GB 只有 6.9 GiB（13.9%）常驻**；引擎 `VmLck 0`、`smaps Locked 0.0 GiB` ⇒ **没有任何页被锁定**。
- **页不过期**：20 分钟前热过的提示再跑 = **0.00 MB / 0.32 s**（冷时 1.11 MB / 2.77 s）。
- 全新随机文本：901 tok **16.25 MB**、1752 tok **34.45 MB**、2660 tok **70.66 MB** ⇒ **18–37 KB/token**，方差大。
- 时间平均：320 请求 × ~34 MB / 8190 s ≈ **1.33 MB/s**，与机主观测的 1–2 MB/s 自洽；容器累计 91.4 GB 的其余 ~80 GB 是启动装载。
- **未证**：驻留率是否低于切 mmap 之前。同一次重启可顺带判：重启后页缓存全冷，若首条冷提示仍读 16–70 MB ⇒ 固有；若 ~0 而数小时后爬升 ⇒ 是回收。

**六、两条纪律（写进本方案，不再只写在报告里）。**
1. **「性能免费」≠「可以拿」**：`P390` 只证明 10-19 栈不掉速（534.83/716.72 vs 532.76/714.89），没证明拿走它有收益；只含安全修复、且该修复被自家 padding 抵消的补丁，收益是 0。
2. **`q8_bytes()` 的 +128 块是隐式不变量**（`moe_mmq.cu:407`）：谁把它改成 `J_max`，就把上游的坑搬回来。改这里必须同时改 `mmq_pad_check.py` 的期望值。

**七、收工仪式：从「拉」改「推」。**
`round_close.py` 只在被调用时检查，而「调用」靠自觉 —— 本轮因此两次漏交四件套（`P410` 自查）。已加：`tools/round_ledger.py`（HARD 第 11 道：本轮必须有 `albus/<round>/reply.md` + `PROGRESS.tsv` 该轮行 + 当日记忆提到该轮）与 `Stop` 钩子（`tools/stop_guard.py`：本回合改过文件且最后一条消息没有四段 ⇒ `{"decision":"block"}`；`PreToolUse` → `round_mark.py` 打标记；fail-open + `stop_hook_active` 防环）。**桌面版是否执行 block 尚未验证。**

### 回写 · W1028–W1034（缺块补记：8 轮只留指针，不追写）

> 事实：方案里最后一个回写块是 `W1027`。W1028–W1034 共 8 轮的结论**只存在于各自 `albus/w10xx/reply.md`**，
> 方案内一个字都没有。这里只补**可检索的指针**，不伪造当时的结论；要回填正文，按行去读那份 report。
> 根因与 `P410` 同源：没有任何门要求「本轮结束前方案里必须多一个块」。W1035 起由 `round_ledger.py` 强制。
"""

TAIL_ROWS = """| `回写 · W1035（P392 重估：补丁不改 tile；decode 不稳的归因；收工仪式改成推式）` | 生产树是 #29953 的 pre-fix，但补丁不改被选中的 tile（J 循环逐字相同）⇒ 数值按构造不变；且 `q8_bytes()` 固定 +128 块余量让热路径本就不越界 ⇒ `-001` vs `-010` 只能记整栈，测不出单条补丁 |
| `回写 · W1028–W1034（缺块补记：8 轮只留指针，不追写）` | 方案里最后一个回写块是 W1027，那 8 轮的结论只活在各自 `reply.md`；本块只补指针，不伪造当时结论 |
"""


def pointer_table():
    rows = ["", "| 轮次 | 该轮报告（唯一正文） | 标题（取自报告首行） |", "|---|---|---|"]
    for w in range(1028, 1035):
        p = os.path.join(ROOT, "w%d" % w, "reply.md")
        title = "（无报告）"
        if os.path.isfile(p):
            for line in io.open(p, encoding="utf-8", errors="replace"):
                if line.startswith("# "):
                    title = line[2:].strip().replace("|", "\\|")[:110]
                    break
        rows.append("| W%d | `%s` | %s |" % (w, p.replace("\\", "/"), title))
    return "\n".join(rows)


def main():
    plan = io.open(PLAN, encoding="utf-8").read()
    if "回写 · W1035" in plan:
        print("W1035 block already present")
    else:
        shutil.copyfile(PLAN, PLAN + ".bak_w1035e")
        lines = plan.split("\n")
        # insert after the last top-level section that follows the W1027 block
        start = next((i for i, l in enumerate(lines) if l.startswith("### 回写 · W1027")), None)
        if start is None:
            print("!! W1027 block not found")
            return 2
        end = len(lines)
        for i in range(start + 1, len(lines)):
            if lines[i].startswith("## "):
                end = i
                break
        block = BLOCK_1035
        if "**那 8 轮**" in block or "下一块" in block:
            block = block.replace("见下一块的指针表", "见块末的指针表")
        block = block.rstrip("\n") + "\n\n**W1028–W1034 指针表**\n" + pointer_table() + "\n"
        lines[end:end] = block.split("\n")
        io.open(PLAN, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
        print("inserted W1035 block + pointer table at line %d" % (end + 1))

    plan = io.open(PLAN, encoding="utf-8").read()
    head = "| `回写 · W1028–W1034（缺块补记：8 轮只留指针，不追写）` |"
    w35 = "| `回写 · W1035（P392 重估：补丁不改 tile；decode 不稳的归因；收工仪式改成推式）` |"
    if w35 in plan:
        print("directory rows already present")
        return 0
    lines = plan.split("\n")
    last = max(i for i, l in enumerate(lines) if re.match(r"\| `回写 · W10\d\d（", l))
    lines[last + 1:last + 1] = [r for r in TAIL_ROWS.rstrip("\n").split("\n")]
    io.open(PLAN, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
    print("directory +2 rows after line %d" % (last + 1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
