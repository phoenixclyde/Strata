# -*- coding: utf-8 -*-
"""追加 W709b（解码校准：实测最优 + 固化）到今日日志"""
import io, os
P = r'D:/workbuddy/.workbuddy/memory/2026-10-08.md'
SEG = """

## W709b ---- 回答「是不是最优」：先定义判据，再用 calibrate 实测解码侧（机主令「你定，我怎么知道最佳是多少，以事实为依据」）

### 1) 先把「最优」定义成可证伪的判据
- 目标函数分层：**D1 解码吞吐（主）** = 单流 512-token、temp0/top_k1/top_p1、预热后 3 次中位；
  P1 预填（固定 18,083-token 冷 prompt，3 次中位）；P2 多轮 TTFT；C1 容量；R1 资源。
- **本机分辨力（本波 8 个读数复现了技能 §7.8 的结论）**：预填同臂内 3 次极差 **1.2~1.7%**、解码 **9.5~15.0%**。
  => 采纳规则：预填须 >2%、解码须用**交错多轮中位**；单次口径的解码差异一律判"不可分辨"。

### 2) 校准窗口（唯一入口 `tools/calibrate.py`，它是上游自带的 A/B 机器）
- **窗口 `01:00:13 -> 01:16:25`（929 s）**：停生产 -> 起**同镜像**临时容器 `strata-calib`（同挂载/同设备/无 restart policy）
  -> 容器内跑 calibrate -> **无条件恢复生产**（`PROD_UP=1`）。
- 校准用 config 另开（`log`/`model_name`/profile-save 都另设）=> **生产日志 0 污染、生产 config md5 未变**。
- **sweep 全表**：`--pcie-frac` 0.00=35.19 / **0.20=35.68** / 0.35=32.76 / **0.36(我们原 auto)=33.71** / 0.55=30.95 / 0.75=29.05；
  `--spec-min-p` 0.30=33.74 / **0.50(我们原值)=35.72** / **0.70=36.96**；
  `--pool-workers` **21(=默认)=36.0** / 14=34.8 / 10=34.2 / 5=29.1；
  adapt（every/swaps/decay）**default=39.7** / 1-80-0.97=33.6 / 1-160-0.97=33.4。
- **交错确认（各 3 次）**：`0.36/0.5` 中位 **33.73** vs `0.20/0.70` 中位 **37.42** = **+10.9%**。

### 3) 本机独立复核（自己写的交错 A/B/A/B，防单一来源）
- A 基线解码 43.7 / 42.2（中位 42.95）；B 校准 46.8 / 46.8（中位 **46.80**）=> **+9.0%**；预填两侧均 455.5~455.8（**不动**）。
- **两个互相独立的方法同向同量级（+9.0% / +10.9%），且预填不变** —— 与 calibrate 的设计声明
  （"Decode speed only: the prompt path streams every expert whatever these settings say"）一致 => **采纳**。

### 4) 落地与固化
- `PARAM_REGISTER.tsv`：`P25 --pcie-frac 0.20`、`P06 --spec-min-p 0.70` 转 ADOPTED（带 sweep + 确认数字）；
  `P26 --pool-workers`、`P27 adapt 三件` 转 **REJECTED**（实测默认最优）；`P24` 转 ADOPTED。
- `gen_config.py --write` -> 生产 config md5 **`8847728605528012c65cebe5048172ce`**；重启 40 s 就绪；真实推理自检通过。
- **`verify_config.py` 复验 `PASS=14 / FAIL=0 / SKIP=1`**（SKIP 是 scope=TOOL 的 P24 —— 顺手补了 TOOL 分支，原缺）。
- 证据归档 `params/evidence/w709_calib_out.json`（md5 `5a39b6a08bc92d25073fb960f007d08f`）。

### 5) 预填侧实测（一项被否、一项待测）
- **`--prefill auto:16384` 实测无效果**：预填 454.05 vs 455.05 = **-0.22%**（分辨力 1.2~1.4%）；解码 +1.5%（不可分辨）=> P22 转 REJECTED。
  与技能 §7.7 在 0.1.39/Q4 上对 `--prefill 16384` 的实测（无收益）**一致**。
- **`STRATA_PREFILL_CPU_SHARE=auto` 未测**：其官方口径是 "prompt<1024 快 19~35%，2K 以上不变"，需要**短 prompt 口径**的探针。
"""
b = SEG.encode('utf-8')
assert b.count(b'\r') == 0
with open(P, 'ab') as f:
    f.write(b)
t = io.open(P, encoding='utf-8').read()
print('bytes =', os.path.getsize(P), 'CR =', open(P, 'rb').read().count(b'\r'))
print('has W709b =', 'W709b' in t)
