#!/usr/bin/env python3
import io
sec = """
## 13:3x W940 · 报告标准立档 + dot4/dot8 定性（含一次我自己造成的二进制污染）
- **报告标准**：`deploy/REPORT_STANDARD.md` —— 四件套第一项**固定 8 个字段**（容器/镜像 id、引擎 md5+大小+version、config md5+exe+args/env、健康 status/restarts/started、ulimit+VmLck、显存布局 cache/borrows/VRAM free、回滚件+可执行命令、本轮改动），第二项 6 字段，第三项 4 字段，第四项 4 字段+队列。**没有数据的字段写 `—`，不能删行。** 起因：W939 那轮第一项只剩 3 行。
- **dot4/dot8 实测（0.1.56 fatbin，68 个 code object）**：`v_dot4_i32_i8` **146,604**（0.1.55 是 130,808，+12.1%）、`v_dot8_i32_i4` **0**、`v_fmac_f32` 122,684、总指令 3,782,033 / 3,290 内核。源码 `sdot8`/`__builtin_amdgcn_sdot8` 在 strata 与 llama.cpp **各 0 处**；`dot8` 命中的 4 个文件是 FP32 辅助函数名（W909 已核）。
- **定性**：**dot4 不是移植项** —— 它一直在跑，问题是供给率 4.55/21.52=21%，不是有没有。**dot8 = 0 条**，方案里只有 R73(验证 DONE) + R74(精度门 OPEN)，**「改内核」这一步凭空缺失** ⇒ 新立 **R84**（仅 gate/up 的 Q4_K；down 的 Q5_1 是 5-bit 塞不进；前置 R74 的 KL≤0.005；路径断言 Q4_K 实例内 v_dot4 减半 + 出现 v_dot8；上限端到端 3.22%）。
- **依据复用**：`vecdotq.cuh` md5 `32877fbe…` 与 W924 当时那份**逐字节相同**（llama.cpp 固定 3cf03257、rebase 未动 third_party/ggml）⇒ W924 三段配比 5,184/1,437/1,204/1,064/824 对 0.2.10 仍成立，R84 上限无需重算。（`mmq-config-gcn.cuh` 两份不同，是 R60 在 work/r60-gc 翻 stream_k=true 造成的，预期内。）
- **事故（我造成的）**：`llvm-objcopy --dump-section=.hip_fatbin=f.bin /data/bin/strata-0.1.56` —— **objcopy 只给输入不给 `-o` 会把结果写回输入**，磁盘件被从 42,924,432 改成 42,898,432（ae085365→7afc2bbf），而进程持旧 inode（`/proc/20/exe (deleted)`）⇒ 服务无感、账本失真、下次重启会静默换版本。**已修**：`docker cp build-r28/strata → .new` + `mv`，三方复核 disk=build=running=ae085365。
- **纪律 ⑯**：任何分析工具对生产二进制必须只读（先 cp 到 /tmp 或显式 `-o`）；同类 `strip`/`patchelf`/`llvm-strip`。**纪律 ⑰**：四件套第一项第 8 项 `disk/build/running 三方 md5 一致`是硬要求 —— 它正是能当场暴露这类污染的字段。
- 产物：`deploy/REPORT_STANDARD.md`、`deploy/W940_DOT4_DOT8_AND_PLAN_GAP.md`；PROGRESS **R84(OPEN)**；W832 队列 `… → R74 → R84 → R49`。
"""
p = "D:/workbuddy_space/strata_ws/.workbuddy/memory/2026-11-04.md"
with io.open(p, "a", encoding="utf-8") as f:
    f.write(sec)
print("ok", len(sec))
