# -*- coding: utf-8 -*-
"""补账：两条 DONE_NEG + R88 正文改靶 + 参数册补两条。"""
import io, time

TS = time.strftime("%Y-%m-%d %H:%M")

# ---------- 1. PROGRESS：补两条负面结论 + R88 改靶 ----------
p = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
lines = io.open(p, encoding="utf-8").read().splitlines()
out = []
added = 0
for l in lines:
    if "\tR88\t" in l:
        cols = l.split("\t")
        cols[2] = ("prompt 路径首块重叠：把「CPU 出专家」与「GPU 首段计算」并行（原表述为异步分阶段拷贝，"
                   "W983/W984 证据改为首块串行：303 tok 时 5.4 ms/token vs 稳态 1.28）；"
                   "外证 llama.cpp#28414（串行上传主导 TTFT）、社区 fork pin+第二流预取 prefill +64%、ktransformers expert deferral")
        cols[7] = "OPEN"
        cols[8] = ("**W983 改靶（%s）**：`--prefill` 借用量 7.62→3.11 GiB 无影响、`pool-tasks` 与 `pcie-frac` 双向均无效应 ⇒ "
                   "不是拷贝量问题，是首块 CPU/GPU 串行。判据：TTFT 2K 4.07 s → ≤3.0 s，decode 不变。" % TS)
        l = "\t".join(cols)
    out.append(l)

rows_to_add = [
    "\t".join(["B1参数轴", "P252", "`--pool-tasks` 6（每 GU/Down 阶段批任务数，默认 3）",
               "W983", "count", "1", "1", "DONE_NEG",
               "**W983 判否（%s）**：走 cfg_apply，TTFT 2K 4.1005 s 对基线 3.948 s = +3.87%%，超出带宽 0.80%% ⇒ 自动回滚。" % TS]),
    "\t".join(["B1参数轴", "P253", "`--pcie-frac` 双向（0.10 / 0.35 对 0.20）",
               "W983/W984", "count", "1", "1", "DONE_NEG",
               "**W983/W984 判否（%s）**：n=10 复核后 0.35 的 TTFT −0.53%%（带宽 2.24%%）、decode −1.88%%（带宽 11.68%%）⇒ 不显著；"
               "0.10 同样不显著。**关键教训**：n=5 时同一改动读作 −1.50%%（假阳性）；未重启基线会造出 +4~5.7%% 假退化（空操作臂证实）。" % TS]),
]
txt = "\n".join(out + rows_to_add) + "\n"
io.open(p, "w", encoding="utf-8", newline="").write(txt)
print("PROGRESS: +2 DONE_NEG, R88 正文已改靶")

# ---------- 2. PARAM_REGISTER：补 --ple-io mmap 与 STRATA_DECODE_TIMING ----------
q = "D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv"
rl = io.open(q, encoding="utf-8").read().splitlines()
head, body = rl[0], rl[1:]
new = []
for l in body:
    c = l.split("\t")
    if c[0] == "P138" and c[2].startswith("--ple-io"):
        c[5] = "ADOPTED"
        c[10] = (c[10] if len(c) > 10 else "") + \
            (" 【W976 改判 %s】生产已改 `--ple-io mmap`（= mmap+不锁；`ram` 是同一路径 + mlock，源码 generate.cpp:5096）："
             "Locked 26.82 GiB→0、MemAvailable 18.8→45.8 GiB、decode 39.7 vs 39.5、prefill 545/548 vs 508/551 ⇒ 等价且内存可回收。"
             "原 REJECTED 针对的是 `direct`。" % TS)
        l = "\t".join(c)
    new.append(l)

extra = [
    "\t".join(["P254", "CLI", "--ple-io mmap", "mmap", "ram", "ADOPTED", "-", "-",
                "P138,P141", "W976：Locked 0 / MemAvailable 45.8 GiB / decode 39.7 / prefill 545·548",
                "**W976 采纳（%s）**：`ram` 即 mmap+mlock；改纯 mmap 后性能等价、26.8 GiB 变可回收，并恢复 arena THP（AnonHugePages 70.47 GiB）、加载 2.95→3.43 GiB/s。" % TS]),
    "\t".join(["P255", "ENV", "STRATA_DECODE_TIMING", "1", "observe", "REFERENCE", "-", "-", "-",
                "每 4 个窗口打一行 decode timing（含 adapt/verify/draft 分解）",
                "**W985 补登记（%s）**：生产常驻的观测开关，此前未入册。它是 R88 定位首块串行的主要手段，保留；代价未测（每 4 窗口一行 stderr）。" % TS]),
]
io.open(q, "w", encoding="utf-8", newline="").write("\n".join([head] + new + extra) + "\n")
print("REGISTER: P138 改判 + P254/P255 新增")
