# W826 · 明天开工清单（P0 `calibrate`）

> 写于 2026-10-30 02:25，收工前。生产此刻 HEALTHY、配置指纹 `23da2da1…`、无残留进程/容器。
> 本件的目的：明天不必重新推导，照着做即可。

---

## 0 已经替你准备好的（今天已做完，不用重做）

| 项 | 位置 | 状态 |
|---|---|---|
| calibrate 用的副本配置 | `/home/albus/strata166/data/w826_calib.json` | 已生成；`log=/data/w826_calib.log`（独立，不污染生产日志） |
| 原件备份（calibrate 会改写副本） | `data/w826_calib_orig.json` | 已备 |
| 生产指纹断言 | `albus/w826/mk_calib_cfg.py` | 跑一次就会断言 `before == after`，已通过 |
| 测量协议 | `albus/r5/mt_read.py` 第 8 参数 `WARM`（默认 2） | 已改并实测（`warm0 3.63 → warm1 3.28 → rep0 3.34 s`） |
| 判据 | 3 轮交替（ABBA）+ 每轮都赢 + 中位超阈值 | 已写进 `W825_ROADMAP.md` §3.3/§6 |
| 数值债账本 | 8 项（补齐 `GDN_HEAD/GDN_PP`） | `W825 §3.2` + register P171 |

---

## 1 明天第一件事：跑 `calibrate.py`（一次窗口，30-45 min）

**为什么是它**：上游 `tools/calibrate.py` 自带 `warm_up(2)` + `SWEEP_ROUNDS=3`（交替）+ 「每轮都赢 + 中位超 3%」——
这三件我们的自制脚本一件都没做（`AUDIT11 §3.3`）。跑它一次 = **同时标定 5 类参数 + 把测量协议校准到上游标准**。

**它会标定**：`--pcie-frac` · `--spec-min-p` · `--pool-workers` · `--adapt-every/swaps/decay` · `--prefill-pipe` ·
`STRATA_SH_STREAM`（AMD 专属，上游实测同卡族有的机 +6~11%、有的 −12~45%，**输出相同**）。

### 步骤

```bash
# 1) 准入检查（不碰生产）
ssh albus@192.168.50.166 '
  df -h / | tail -1                 # 需 >30 GB（现在 238 GB）
  grep -E "^MemAvailable" /proc/meminfo
  curl -s --max-time 3 http://127.0.0.1:8090/health >/dev/null && echo PROD_HEALTHY
  ls -la /home/albus/strata166/data/w826_calib.json'

# 2) 停生产（这是唯一必须停的环节）
docker stop -t 25 strata166-407

# 3) 跑 calibrate（后台，日志落盘；它会自己起停引擎若干次）
cd /home/albus/strata166/src0271 && \
  setsid nohup python3 tools/calibrate.py /home/albus/strata166/data/w826_calib.json \
  > /home/albus/strata166/data/w826_calib.out 2>&1 < /dev/null &

# 4) 盯进度（它有 print 输出，看 w826_calib.out）
tail -f /home/albus/strata166/data/w826_calib.out

# 5) 收工必做：恢复生产
docker start strata166-407
# 然后等 /health（热启 165-260 s，因为换权重后 arena 71.7 GiB）
```

### 判据

- calibrate 返回的 JSON 里，**每个胜出项**的增益都应 ≥3%；它自己的判据更严（每轮都赢）。
- **不要直接采纳进生产**。先人工审：`apply_args` / `apply_env` 会把结果写进 `w826_calib.json`，
  比对它相对 `w826_calib_orig.json` 改了哪几个字段。
- 再用我们的协议（warm_up 2 + 3 轮交替）在生产上复核，**≥5% 才上生产**（本机规矩比上游的 3% 严）。

### 风险与回滚

| 风险 | 处置 |
|---|---|
| calibrate 中途崩、生产未恢复 | `docker start strata166-407`（配置没动，一定能起） |
| 它把 `STRATA_SH_STREAM` 写进 env | **人工审**：该开关在 AMD 上方向不定（+6~11% / −12~45%），必须我们自己在生产上复测一次才采纳 |
| 停机时间超预期 | 它内部会多次重启（pool-workers / adapt-* / SH_STREAM 每值一次）。若超 60 min 未见结果，`kill -9` 后直接恢复生产，改天再跑 |
| 磁盘/内存不足 | 准入检查里已含（现在 238 GB / 46 GB 可用，够） |

---

## 2 如果 P0 顺利，接着做 P1（数值债总量，12-15 min，同一个窗口内可做）

两臂：**当前全量** vs **最小近似**（`RT_SKIP=0` + `--kv fp16` + `PROMPT_F16=0` + `SELECT_SIMT=0` + `HC_Q8=0`）。

- **必须 `STRATA_PREFILL_CPU_SHARE=0`**（否则底噪 0.025 与效应 0.026-0.046 同量级，只能得「判不了」—— W824 的教训）。
- 判据：底噪必须为 0（三份 LOGPOS 同哈希）；总量 **<0.02 则 8 项全部结清**，**>0.05 再二分**。
- 这轮量的是 8 项叠加的总账，比逐项关（8 项 × 2 臂 = 16 次启动）便宜一个数量级。

---

## 3 一个必须记住的副作用

`mt_read.py` 的 `WARM` 默认已改 2 ⇒ **新测的短档会比历史数据快 10-15%**（去掉了约 1 s 冷启动）。

> 新数据与 W804/W810/W822/W824 的**绝对值不可直接比**，只能比同批次内的相对差。
> 引用旧数据时必须标注「该读数未预热」。

---

## 4 今天留下的三个未做项（都不阻塞 P0）

| # | 项 | 为什么没做 |
|---|---|---|
| 1 | `--spec 5/6`、`--prefill` chunk 的 A/B | 机制上偏负（槽位覆盖 30.7%，窗口越大 miss 越多），优先级在 P0/P1 之后 |
| 2 | 移植 #3220（HC_Q8 prefill 反量化向量化，上游 1.95x、bitwise） | 要动内核代码 + 重编译，估 1-2% prefill，排在最后 |
| 3 | 换权重的精度收益验证 | **已不可逆**：IQ4 已删（174.5 GiB），要复核需重下 88 GB |

## 5 事后注记（AUDIT12，2026-10-31）

实际顺序与本清单**相反**：先升了 0.1.54（W828 §6.2），calibrate 才在 **0.1.54n** 上跑（W828 §6.3/§6.7）。
所以 §1 的"先在 0.1.53 上跑 P0"已作废；而 calibrate 两次给出的建议**互相矛盾**（W828 §6.7），
其中"每值重启"那类臂不可信 —— 结论是：**calibrate 只可作为候选生成器，不可直接采纳**。
另 §2 的"8 项总量"实测只翻了 5 项（W828 §6.10 / AUDIT12）。
