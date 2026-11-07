#!/usr/bin/env python3
# W936 memory append
import io
sec = """
## 11:2x W936 · R77 采纳：GPU 致命错后自退 + 服务端 503 可重试（e1b27d54 / #4350）
- **移植**：四部分 —— `generate.cpp`(+43，1 处上下文冲突)、`serve/server.py`(+46，干净)、`serve/test_fatal_gpu_restart.py`(+82)、`src/dsv41/ds4_main.cpp`(+38，我们不跑 DeepSeek)。**无 HIP 宏门控** ⇒ P257 不适用；`cudaPeekAtLastError/cudaGetErrorString` 在 `strata_hip.h:83/80` 有映射，且 `generate.cpp:16052` 本就在用。
- **冲突根因**：上游插入点靠 `engine_main`（0.2.10 才把 main 拆成 engine_main + Windows 壳），我们是裸 `int main`（2906 行）⇒ 把两个函数插在 `int main` 之前，四个调用点（ver.run 前 / ver.run 失败分支 / commit 失败 / wait_commit 失败）按原样插。用唯一锚点脚本替换，**没有** sed 全局改（P257）。
- **实测**：`STRATA_INJECT_FATAL=2` → **首请求 503(1.3s)**，报文 `fatal GPU error ... the next request restarts it` → 引擎 `_Exit(3)` → **同一请求内自动重启(268.8s)** 并出 8 token → 后续 200/0.4s。**注入数的是 decode 窗口不是请求**（max_tokens=8 就 2 窗口）⇒ 命中在 req1 而非上游说的 req2。
- **服务端记账在 `docker logs` 而不是引擎日志文件**（server 的 `print()` 走 stdout）：`engine ended (exit code 3) and is started again ... (1 of 3 allowed in 10 minutes)` + `the engine had stopped (exit code 3); starting it again`。**上游 7 个单测全过**（1/3→2/3→3/3 递进、普通 ERR 仍 400、同一具尸体只算一次）。反向：`messages=[]` → 400 且引擎 pid 不变。
- **零回归**：prefill 8.853→8.868(+0.17%，CV1.1%)、decode 稳态 79.44 vs 79.4。二进制 `8e92c662`→**`cf2ba243`**（+2576 B），server.py `b1aa1d36`→**`7dfcc000`**。
- **部署脆弱点（P261）**：`/src` **不是 bind**（容器只有 `/models` ro 与 `/data` rw），`server.py` 是镜像层 ⇒ **容器重建会丢补丁，且不崩**（fatal 错又退回 400）。已持久化 `/data/w936/server.py.r77` 与 `.bak`。根治=重建镜像烘进去（未做）。引擎在 `/data/bin`（bind）不受影响。
- **新坑（纪律 ⑪）**：`clang ... 2>&1 | grep -E "error" | head -20` → `head` 读满关管道 → clang **SIGPIPE 被杀**，对象半截、链接后 md5 与原来一模一样，`set -e` 也看不出来（管道退出码是 head 的）。**编译器输出必须 `> log 2>&1` 再单独取 rc**。
- **另一个自查**：登记脚本改了 R77 那行却**忘了写回文件**（只 append 了 R79），进度数不动才发现。⇒ 改账本必须校验「改后的值」而不是「打印的日志」。
- 产物：`deploy/W936_R77_FATAL_GPU_ADOPT.md`；`PROGRESS.tsv` R77(DONE) + R79(OPEN，重启后会话恢复，上游自述 NOT tested)；`PARAM_REGISTER` P261；`W832` 队列 + 纪律 ⑥⑦（编号接在 W917 那组后）；补丁 `~/strata166/patches/r77_fatal_gpu_on_mainline.patch`；树 `work/r77`；归档 `~/strata166/w936/`。
"""
p = "D:/workbuddy_space/strata_ws/.workbuddy/memory/2026-11-04.md"
with io.open(p, "a", encoding="utf-8") as f:
    f.write(sec)
print("appended", len(sec))
