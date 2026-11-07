## W834：`--pool-workers` 判结（2026-10-31 13:27–13:43）

- 源码口径：`--pool-workers 0` = 每物理核一个（22 核 → 实际 **20 workers + host**，日志 `20 expert-pool workers + the host thread`）；>0 覆盖；只搬线程不改结果。
- 两臂（同镜像 p2 / 同 exe n2 / 只差这个 arg）：decode **51.75 vs 51.55（−0.4%）**；
  read 1958/3718/6666 tok = **−3.2% / +0.3% / +0.3%**（符号翻转）⇒ **无系统差异**，保留默认 0。
- **参数轴四项闭合**：`spec_min_p` UNRESOLVED、`pcie_frac` UNRESOLVED、`pool_workers` 无差异、`adapt 4/96` 默认正确。
  ⇒ 对外只说"没有可分辨收益"，**不说"已调到最优"**。
- 登记 **P214**（216 行）。生产未改，恢复后快照逐项一致（7463 槽/21.79 GiB、97.4%、md5 未变、预热 12850 MB/s）。
- 下一步已备好：数值债 5 项分项（`RT_SKIP=0` / `kv=fp16` / `PROMPT_F16=0` / `SELECT_SIMT=0` / `HC_Q8=0`），
  配置生成器 `albus/w834/a11_klcfg2.sh`，基线 E0 已在场（n=6），每臂 ≈4.5 min，5 臂 ≈22 min。
