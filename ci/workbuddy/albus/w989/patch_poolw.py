# -*- coding: utf-8 -*-
import io, time
TS = time.strftime("%Y-%m-%d %H:%M")

P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
lines = io.open(P, encoding="utf-8").read().splitlines()
rows = [
    "\t".join(["B1参数轴", "P265", "`--pool-workers 10`（CPU 专家池，默认 20=每物理核一个）", "W989", "count", "1", "1",
               "DONE", "**W989 采纳（%s）** n=3/长度、CV 0.18–0.5%%：prefill@2K **524.45 vs 511.73（+2.49%%，band 1.00%%）**、"
               "@8K 705.88 vs 704.32（+0.22%%）、TTFT 3.992 vs 4.074（−2.0%%）、decode 持平。⇒ **20 worker 是过订阅**，"
               "减半反而更快（内存带宽/争用）。**副作用**：`--pool-workers` 使 args 35→37。" % TS]),
    "\t".join(["B5本机缺口", "P266", "采样归因通道（gdb attach）不可用：容器进程的 /proc/PID/exe 在宿主不存在，且 attach 使 4 s 请求拖到 17 s", "W989", "count", "1", "0",
               "OPEN", "**W989 立（%s）**：显式给二进制后主程序符号可解（热点 `ggml_vec_dot_q4_K_q8_K` / `ExpertPool::worker`），"
               "但 60/95 个采样落在 libc 的 syscall 包装上（ioctl/read/nanosleep）——**是 attach 暂停的伪影**，不能当判据。"
               "解除条件：出一份 `-g` 专用构建（只用于采样，不上生产）或用引擎内计时。" % TS]),
]
io.open(P, "w", encoding="utf-8", newline="").write("\n".join(lines + rows) + "\n")
print("PROGRESS: +P265(采纳) / +P266(采样通道 OPEN)")
