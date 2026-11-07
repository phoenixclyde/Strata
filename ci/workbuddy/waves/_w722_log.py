# -*- coding: utf-8 -*-
"""追加 W709 看门狗事故到今日日志（append-only）"""
import io, os
P = r'D:/workbuddy/.workbuddy/memory/2026-10-08.md'
SEG = """

## W709a ---- 校准窗口的看门狗事故（自伤，但未造成损害）

### 背景
要在 166 上跑 `tools/calibrate.py`（独占 GPU；生产容器占 33.9 GB / 共 34.3 GB）⇒ 必须先停生产。
写了「窗口包装 + 独立看门狗」：包装跑完**无条件**恢复生产；看门狗兜底，防包装本身被打死。

### [!] 事故：看门狗判据错了，把生产容器提前拉回
- 包装脚本流程：停 402 -> 起临时容器 `strata-calib` -> `docker exec` 跑 calibrate -> 恢复 402。
- 看门狗 v1 的判据是「**有没有 calibrate 进程在跑**」：没有就起 402。
- 实测时间线（`calib_run.log` + `watchdog.log`）：
  `01:00:13` WINDOW_START / `01:00:19` stop_rc=0 / `01:00:25` 起临时容器 / `01:00:29` **calibrate start**
  `01:00:26` 看门狗第 1 次检查 -> **"no calibrate alive"**（此刻 `docker exec` 还没起来）-> `01:00:39` **它把 402 启动了**
- 后果：**两个引擎同时抢 GPU**。实测 KFD 列表：校准的 strata 已拿到 `33,828,376,576 B`，
  而 402 的 strata 刚起、只占 `42,008,576 B`（尚未分配）——**谁先到谁赢**，这次是校准赢了。
- 处置：`docker stop -t 30 strata166-402`，只留校准；KFD 复验只剩 1 个 strata（`33.8 GB`）。
  **未造成损害**（402 那 42 MB 是进程启动开销，未抢到 VRAM，也未污染任何 config/日志）。

### 根因与修法
- 根因：**看门狗用「载荷进程」当窗口标志，而载荷进程比窗口本身晚起**（包装要先停容器、起临时容器，才轮到 exec）。
- 修法（`watchdog2.sh`，已上线）：判据改为「**窗口包装进程**是否还在」——
  `pgrep -f 'w709/run_calib\\.sh'`：包装在 => 窗口进行中，不动；包装没了 => 恢复生产。
  另加 ~100 分钟超时兜底强制拉起。
- **通用教训**：给「停生产 / 独占资源」的窗口做兜底时，**标志物要用窗口自身（包装进程），不能用它的载荷**
  —— 载荷在窗口内的出现时刻是不确定的，用它会误判「窗口没开始」。
"""
b = SEG.encode('utf-8')
assert b.count(b'\r') == 0
with open(P, 'ab') as f:
    f.write(b)
t = io.open(P, encoding='utf-8').read()
print('bytes =', os.path.getsize(P), 'CR =', open(P, 'rb').read().count(b'\r'))
print('has W709a =', 'W709a' in t)
print('tail:', t.splitlines()[-1][:100])
