# W843 审计证据索引（AUDIT14 用）

| 证据 | 文件 | 支撑哪条 |
|---|---|---|
| 两臂原始输出（18:16 那轮 3 臂） | `evidence/remote_raw.txt` 第 1–6 段 | A 臂误判、A2 read/decode |
| B 臂原始输出（单独重跑） | 同上第 7 段 | B 的 read/decode、SIMT=2 生效 |
| `qsa select` 横幅行号 | 同上 `GREP` 段（76639 = SIMT=2） | "=2 确实生效" |
| 门禁 17 项 | 同上 `GATE` 段 | 生产状态 |
| 容器日志时间线（UTC） | `evidence/arm_a_timeline.txt` | 18:16 的 A/B 两臂 abort 真因（判据太急，非崩溃） |
| 参数登记表状态分布 | `evidence/param_status_after.txt` | 未结 15 条 |
| 四道门源码现场 | `evidence/gates_verified.txt` | 行号 2155/2197/4253/4292 与 4 个调用点 |
