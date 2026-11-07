import io, os
os.chdir(r"D:/workbuddy_space/strata_ws/deploy")

rows = [
 ["B10环境与版本", "R67",
  "PLE 表 26.8 GiB 的 mlock：容器 memlock 只有 8 MiB，表一直以可回收方式驻留（VmLck 0）；改容器 --ulimit memlock=-1 后再测 decode",
  "W919 §2", "count", "1", "0", "OPEN",
  "**W919 立（2026-11-03 22:3x，零停服）**：读 0.2.10 release notes 发现 #4671 原文「a systemd service without LimitMEMLOCK may lock 8 MiB, so the **26.8 GiB mlock of the PLE table was refused** … the reporter measured **up to 6% slower decode**」，26.8 GiB 正是我们 PLE 表的大小（W910 实测 26.82 GiB）。**现场实证**：日志每次 startup 都有 `strata: PLE table mlock failed (Cannot allocate memory; raise ulimit -l)` + `PLE table loaded (not locked)`，`VmLck: 0 kB`；`ulimit -l` = 8192 KiB，`/proc/<engine>/limits` soft=hard=8388608，`HostConfig.Ulimits=[]`，`systemctl show docker LimitMEMLOCK=8388608` ⇒ 容器内 hard 即 8 MiB，非 root 提不动。**最小验证（不碰生产）**：同镜像临时容器 `docker run --rm --ulimit memlock=-1` ⇒ `mlock(256 MiB) rc=0`，生产容器同调用 `rc=-1 errno=12`。**内存账成立**：RAM budget 76 GiB 已含 PLE 26.8 + 专家 33.45 = 60.25 GiB，且专家 cache 走 pinned/mapped（不计 VmLck），放开 memlock 只影响 PLE、不动专家策略。**执行需重建容器**（--ulimit 不能 docker update）：停 → 带 --ulimit memlock=-1 重新 run → 加载 117 s + 服务 230–275 s。**破坏性操作，待机主确认**。判据：VmLck ≈ 26.8 GiB、日志无 mlock failed、TTFT 不劣化、decode |Δ|≥2×CV",
  "W919"],
 ["B4上游移植", "R68",
  "#4677 serve stop bound 移植（243fdb21）：HIP 专用、单请求投机 + park 的最后一窗口快照被截断，避免快照被拒后回退旧 checkpoint（上游实测 4/16→0/16 回退、复用 98.36→99.74%）",
  "W919 §3.1", "count", "1", "0", "OPEN",
  "**W919 立（2026-11-03 22:3x，零停服）**：0.2.10 提交 243fdb21 自述「the last window could park a snapshot with tokens the client never received; conversation_prefix() needs the whole snapshot to be a prefix of the next prompt, so the snapshot was refused and the older checkpoint was used（**about 6% of a 12K-token prompt read again**）」+「**HIP only (STRATA_USE_HIP), where it was measured**」。**形状完全对上**：HIP(gfx906) / 单请求投机(--spec 4) / 对话逐个打开（正是实测有效的场景，非 batch 行）/ 有 park(CKPT_MOVE_PARK=1 + --prompt-cache-every 8192)。我方树 STRATA_SERVE_STOP_BOUND 命中 **0**。改动 = 新文件 serve_stop_bound.hpp(15 行) + generate.cpp(25 行) + CMake(5 行)，**不改数值**（自述与旧标量循环一致，带 2736 例策略测试）。判据：输出逐位相同 + 多轮第 2 轮 prompt 重读量下降；**不需要 KL 门**",
  "W919;W913"],
 ["B6判定探针", "R69",
  "#4590 penalty 窗口移植（ed76b12f）：重复/频率/存在惩罚改按回复自身 token 计，不再吃 prompt 尾部（我们是 Qwen，症状是新任务重复旧 JSON）",
  "W919 §3.2", "count", "1", "0", "OPEN",
  "**W919 立（2026-11-03 22:3x，零停服）**：0.2.10 提交 ed76b12f「the repeat, frequency and presence penalties count the tokens the reply has written, not the last tokens of the prompt；STRATA_PENALTY_PROMPT=1 brings the old window back (#4590)」。报告者 4 消息对话（P100/IQ2_XS）旧 JSON 复现 32 seeds 里 13 次 → 4 次；61 题套件 56/55 → 55。我们是 arch=qwen4exp + 带惩罚采样 ⇒ 会命中。我方树命中 **0**。**会改输出 ⇒ 必须先过 W913 精度门**（KL ≤0.005、top-1 ≥99%，分辨率 0.0032），再判「重复旧 JSON」是否改善。排期放在 R64 之后（不影响 prefill/decode 主战场）",
  "W919;W913"],
 ["B6判定探针", "R70",
  "借 0.2.9「gfx12 chunked 阈值降到 64 token」的调参维度：在 gfx906 上扫 prefill chunk 阈值（现 auto=8192、CPU share 阈值 1024），量 1K/3K/6K 三档 TTFT",
  "W919 §5.2", "count", "1", "0", "OPEN",
  "**W919 立（2026-11-03 22:3x，零停服）**：0.2.9 让 Radeon gfx12 的 chunked kernel **从 64 token 起**（4K +3.5%、16K +4.7%、32K +6.1%），并把选择依据从「计时猜测」改成「按 prompt 长度」（0.2.7）。架构门挡住 gfx906，但**「阈值定在哪」是可借的调参维度**：我们日志为 `strata serve: prompt chunk auto: 8192 tokens, a 96-slot ring`、`prefill: the CPU share is ON by default for prompt chunks below 1024 tokens`。**只读扫描**：在 1024/2048/4096/8192 四档量 1K/3K/6K prompt 的 TTFT（服务端 read in 为准），每组 ≥3 rep、判据 |Δ|≥2×CV。不改代码、零停服；若某档稳定赢再立参数项",
  "W919;W804"],
]

for r in rows:
    assert len(r) == 10, (r[1], len(r))

with io.open("PROGRESS.tsv", "a", encoding="utf-8", newline="") as f:
    for r in rows:
        f.write("\t".join(r) + "\n")
print("appended", len(rows))
