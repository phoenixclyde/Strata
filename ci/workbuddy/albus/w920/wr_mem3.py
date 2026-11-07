import io, os
os.chdir(r"D:/workbuddy_space/strata_ws/.workbuddy/memory")
sec = """
## 23:3x W920 §8 · PLE mlock 严格复测（+0.24%）与机主决定（保留）
- **机主三条指令**：①PLE mlock「用。」→ 保留 `--ulimit memlock=-1`；②`/data/strata-trace` 关掉（已 `.off`）；③**四件套必须带回队列内容**（近几轮我把队列丢了）。
- **严格复测（修正 §7 的冷启混淆）**：两臂都先预热、取 rep6-9 median ⇒ 未锁 decode **79.24** / 已锁 **79.43** = **+0.24%**，prefill 8.845→8.826 s = +0.2% ⇒ **零收益结论不变**。
- **记账纪律（重要）**：`R67` 保持 **DONE_NEG**（实验结论=无收益），配置决定另立 **P256 = ADOPTED**（理由写明"预防性，非性能"）。**把零收益的实验写成"采纳有收益"就是造假**。
- **保留的真实理由**：长时间运行/内存压力变化时，未锁的 PLE 页可能被回收，而日志只在启动时说一次、运行期不自知；锁住后这个风险不存在。代价 available 43→18 GB（PLE 26.82 + 专家 arena 71.73 + 会话缓存 4 + 权重 3.6 ≈ 106 GiB / 125 GB），可承受。
- **当前容器**：`107899e1`（新），`ulimits=[{memlock,Hard:-1,Soft:-1}]`，`VmLck 28,125,140 kB`，`ulimit -l unlimited`，日志 `PLE table locked in RAM … in 1.8 s`。回滚备份容器 `strata166-407.pre-w920b`。
- **纪律**：四件套每轮固定四节，**第四节必须带队列**（不只是百分比）。
- 进度 **86/155 = 55.5%**，主线 **86/127 = 67.7%**。队列 `~~R59~~ → ~~R67~~ → **R66** → R68 → R61 → R60 → R58 → R63 → R64 → R69 → R70 → R65 → R49 → R50 → R30′ → M3`。
"""
with io.open("2026-11-03.md", "a", encoding="utf-8") as f:
    f.write(sec)
print("ok", len(sec))
