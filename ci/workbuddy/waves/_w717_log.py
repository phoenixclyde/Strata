import io

P = r"D:/workbuddy/.workbuddy/memory/2026-10-07.md"
import os
if not os.path.isfile(P):
    io.open(P, "w", encoding="utf-8", newline="").write("# 2026-10-07 工作日志（routeK）\n")
b = open(P, "rb").read()
assert b.count(b"\r") == 0, "CR present"
t = b.decode("utf-8")

SEG = """

## W706 ---- 166 的 Z0 已清掉（机主令「你就把166的z0状态清掉就行了」）

- **Z0 = 性能档三件**：GPU `perflevel` / CPU `scaling_governor` / THP `enabled`。
  `on`（性能档）= `high` / `performance` / `always`；`off`（省电/对照档）= `auto` / `schedutil` / `madvise`。
- **执行前实测（三件全在 Z0-on）**：`perflevel=high` / `governor=performance` / `THP=[always]` / defrag `[madvise]`
  / `cur_freq_khz=3700000` / `gpupower=22.0W`。
- **工具**：`run/_zk5_z0off.sh`（3058 B / `5ffa9e7c7b2c4b9a8d079e0142ddae23`，2026-09-19 建）；
  三条动作 = `sudo -n rocm-smi -d 0 --setperflevel auto` + `sudo -n cpupower frequency-set -g schedutil`
  + `echo madvise | sudo -n tee /sys/kernel/mm/transparent_hugepage/enabled`。
- **执行后实测**：`perflevel=auto` / `governor=schedutil` / `THP=[madvise]` / `cur_freq_khz=1320177` / `gpupower=17.0W`。
- **自证**：工具自打 `Z0OFF_DONE mode=off` + `Z0OFF_VERIFY_OK perflevel=auto governor=schedutil thp=madvise`；
  复读判定 `Z0_OFF_VERIFY_OK=1`（三件均达 off 态）。
- **副作用（实测）**：`cur_freq_khz 3,700,000 -> 1,320,177`（CPU 降频）· `gpupower 22.0W -> 17.0W`。
  => **这是省电/对照档，不是性能档**。按 `ENV-03` 判据面：**此后引用任何性能读数必须声明 Z0=off**。
- **复归性能档**（备忘）= `bash run/_rk78_z0_state.sh`（状态驱动幂等，把三件设回 `high/performance/always`）。
- 现场：166 `up 15:58`，`boot_id = 46715f3e-6a2d-44a0-b1ce-4245628c86da`，`sudo -n` 可用（SUDO_NOPASSWD_OK）。
- **开机机制现状**（本轮顺带探明）：`/etc/systemd/system/` 下自建的只有 `fanctl.service` / `fanctl-watchdog.service` /
  `opencode-serve.service`；**无 Z0 相关 unit**；`rc.local` 不存在；`crontab`（albus 与 root）均空；
  `/etc/udev/rules.d/` 只有 snap + LVM 三条。=> **Z0 确认未做成开机自动**（与 `BACKLOG` 的 `ENV-03`
  「Z0 三条未脚本化为开机流程」一致）。
- 产物：`D:/workbuddy/_z_rk81/_pr81_z0probe.py`（现状+机制探针）、`_pr82_z0off.py`（执行）及对应 `.out.txt`。
"""

io.open(P, "w", encoding="utf-8", newline="").write(t + SEG)
nb = open(P, "rb").read()
print("log %s bytes=%d CR=%d" % (P.split("/")[-1], len(nb), nb.count(b"\r")))
tt = nb.decode("utf-8")
for k in ["## W706", "Z0_OFF_VERIFY_OK", "1320177", "ENV-03"]:
    print("  has %-20s : %s" % (k, k in tt))
