import io

p = 'D:/workbuddy_space/strata_ws/deploy/W776_TUNING_MASTER_PLAN.md'
s = io.open(p, encoding='utf-8').read()

old_r0 = """### 12.3 新增 R0（排在最前，1 次重启约 45 s）

**在 `schedutil` 下重建基线**：三档各 3 runs，取 `decode GPU stages` 的 `hc_down / hc_up / gemv / router` 四个数。
理由：现存基线全在 `performance` 下测（`P97`），不重建则任何对照都夹带 governor 差异，而这恰好落在可判下限的量级上。"""

new_r0 = """### 12.3 R0 已完成（2026-10-25 13:56-14:19，见 `W790`）

**基线（`schedutil`，HC_Q8=1，M 档 97 窗口）**：total **47.19 / 47.51**，hc_down **3.60-3.62**，hc_up **3.51-3.53**，
gemv **6.09-6.11**，router 3.81-3.87，attn 3.34-3.36，专家流 10.35-10.55（`P98`）。

**两件顺带解决的事：**

1. **governor 差异已量化**：同进程交错 3 对，`performance` 中位 47.03 vs `schedutil` 45.94 = **schedutil 快 2.3%**，
   三对全部同向（`P97` 更新）。所以把 W776 遗留的 `performance` 改回 `schedutil` **不是回归而是改善**；
   现存 performance 时代基线（`P91` 46.35、`W788` 51.58、R5 53.17/53.02）**偏悲观约 2%**。
2. **R5 那个"+3% 回归"被解释掉**：它与 governor 偏差（2%）+ 预热偏差（3%，见 §12.4）同量级，本来就不该判成回归。

### 12.4 测量协议（新增两条，硬性）

- **丢弃重启后前 2 个请求**。实测：第 1 次请求专家流 17.44（稳态 10.3）、total 54.86；第 2-3 次 47.5/47.2；
  同一配置在第 4-9 次为 45.7-46.7。`--expert-cache auto` 是按请求逐步填充的，**不丢弃则基线偏高约 3%**。
  过去所有"3 runs"（含 `P91`）都可能含 1 个偏冷样本。
- **A/B 必须同会话交错**，并在每臂记录 governor。跨会话的 total 摆 45.7-47.5（约 4%），同会话内只 ±1.5%。"""

assert s.count(old_r0) == 1, s.count(old_r0)
s = s.replace(old_r0, new_r0, 1)

old_r5 = '| **R5 HC**（down+up） | 7.42 | 16.1% | >= 6% | 省 0.45 ms |'
new_r5 = ('| **R5 `up`**（结构余量已测） | 3.44 | 7.4% | >= 10% | 省 0.34 ms（可达 2.96） |\n'
          '| ~~R5 `down`~~ | 3.47 | 7.5% | — | **暂不排**：对 int8/bf16 完全不敏感（都是 3.47），需 profiler |')
assert s.count(old_r5) == 1, s.count(old_r5)
s = s.replace(old_r5, new_r5, 1)

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('W776 12.3/12.4 + R5 retarget done')
