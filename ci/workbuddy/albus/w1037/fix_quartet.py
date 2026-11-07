import io, shutil

P = "albus/w1037/reply.md"
shutil.copyfile(P, P + ".bak_w1037f")
s = io.open(P, encoding="utf-8").read()

pairs = [
 # 4 健康
 ("restarts=0 · StartedAt `2026-11-06T22:13:59Z`（= 本机 06:13:59，W1036 A0 窗口还原后的启动）",
  "restarts=0（docker 的 RestartCount 只计策略重启）· StartedAt `2026-11-06T23:26:40Z`（= 本机 07:26:40，**本轮 A/B 窗口还原后的启动**）"),
 # 6 显存
 ("VRAM used 33,586,655,232 B / total 34,342,961,152 B ⇒ **VRAM free 756,305,920 B（0.70 GiB）**",
  "VRAM used 33,583,194,112 B / total 34,342,961,152 B ⇒ **VRAM free 759,767,040 B（0.71 GiB）**（窗口还原后取）"),
 # 8 本轮改动
 ("**引擎无净变更**：disk `-001` = running = 5e63174d… 三方一致；生产 **0 次装机、0 次重启、0 分钟停机**。改动全部在分支 `gfx906/port-all`（新提交 `8b44f3d1`）与 166 的临时目录",
  "**引擎无净变更**：disk `-001` = running = `5e63174d…`，config md5 回到 `53ac61e0…`；"
  "本轮**装机 1 次（候选 pa1，窗口内，已还原）/ 重启 3 次 / 停机 136 s / 回滚 0 次**。"
  "源码改动全部在分支 `gfx906/port-all`（`8b44f3d1`）与 worktree `pr/k10`"),
 # 三、落生产
 ("**三、本次落生产** — **重启 0 次 / 停机 0 分钟 / 回滚 0 次 / 装机 0 次**。全部工作落在「读现场 + 改分支 + 在镜像内增量编译 + 写文档」。\n唯一会碰生产的动作是**计划中的 A/B 窗口**（三次重启、约 5–8 min 不可用），脚本已就位、**未执行，等点头**。",
  "**三、本次落生产** — **重启 3 次 / 停机 136 s / 回滚 0 次 / 装机 1 次（已还原）**。\n"
  "窗口 07:23:02–07:27:25，三段重启各 47 s / 42 s / 47 s（容器 stop→`/health` ok 的实测间隔），期间候选 `pa1` 一度在产、结束后还原 `-001`；\n"
  "还原后 config md5 `53ac61e0c663a6a46b7a5aa2e610bf43`、engines=1、`/health` ok。其余工作全部落在「读现场 + 改分支 + 镜像内编译 + 写文档」。\n"
  "**窗口结论**：三臂在 8K 上差值 −0.10% / −0.02%（当次 2×CV **0.20% / 0.00%**）⇒ 零效果；`qsa attn` 相位逐毫秒不变 ⇒ 改动不在热路径（详见正文 §13）。"),
]
for a, b in pairs:
    if a not in s:
        print("WARN anchor missing:", a[:40])
        continue
    s = s.replace(a, b, 1)
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("reply 四件套已按窗口后现场改写")
