# HANDOVER ---- Strata 工作区交接（2026-10-08）

> 运行期交接请看 **`deploy/W709_HANDOVER.md`**（§2 机制 / §3 五项待测配方 / §4 避坑）。
> 本件只交代**这次迁移**做了什么、怎么自证、从哪继续。

---

## 一、这次做了三件事

1. **建独立工作区** `D:/workbuddy_space/strata_ws/`，把 Strata 资产从 routeK 工作区整体迁出。
2. **搬对了才删原**：逐文件 md5 校验两侧全等（`ALL PASS`）之后才删除源目录。
3. **补齐自包含件**：`PROJECT.md`（入口）· `MAP_OLD_TO_NEW.md`（路径映射）· `.workbuddy/memory/`（记忆）。

## 二、迁移清单与指纹

| 项 | 旧 | 新 | 规模 | 校验 |
|---|---|---|---|---|
| 部署件 | `D:/strata166/` | `deploy/` | 6,698 文件 / 219,152,974 B | md5 全等 PASS |
| 波次件 | `D:/workbuddy/_z_rk81/` | `waves/` | 165 文件 / 582,840 B | md5 全等 PASS |
| 今日记忆 | `D:/workbuddy/.workbuddy/memory/2026-10-08.md` | `.workbuddy/memory/2026-10-08.md` | 30,491 B（+W710 段 = 31,691 B） | md5 MATCH |
| Z0 基线 | `D:/workbuddy/.workbuddy/memory/2026-10-07.md` | `.workbuddy/memory/2026-10-07.md` | 2,195 B | md5 MATCH |

- **未迁**：`D:/Strata/`（11.2 GB Windows 部署包，7194 文件）---- 机主令留原地，见 `PROJECT.md` §六。
- **就地修一处**：`waves/_gh.py` 的 `TOKF` 指向新址（运行时唯一真要读的路径）。
- **外部引用同步**：技能 `flashnext-engine-selection/SKILL.md` 里 2 处 `D:\strata166\docker\` 已改指新址。
- **历史件旧路径逐字保留**（交付件正文与一次性脚本是证据，不篡改）；换算表见 `MAP_OLD_TO_NEW.md`。

## 三、迁移的自证

- 校验器：`tools/_verify_copy.py`，判据三条（文件集一致 / 字节数一致 / md5 一致），任一条不过即 `FAIL` 且**禁止删原**。
- 输出：`tools/_verify_copy_out.md`（本次 `ALL PASS`）。
- routeK 侧原 `2026-10-08.md` 改为**指针存根**，不静默消失。

## 四、明天从这里继续

1. 先核现场：容器 `strata166-404` 是否 `Up`、`http=200`、LIVE config md5 是否仍为 `d2b10f0c4e8293ba010614c7acc70bea`。
2. 按 `deploy/W709_HANDOVER.md` §3 推进**五项未测** + 补 P34 的 `>16k` / `<8k` 两档。
3. 重跑**独立对抗性审计**（上一轮子 agent 通道 3 次被 killed，只到机械化证据链 35/36）。
4. 改参数**只走** `PROJECT.md` §四那条通道（register -> gen_config -> 推 166 -> restart -> verify FAIL=0）。
5. 引用任何性能读数，**必须带 `Z0=off`**。
