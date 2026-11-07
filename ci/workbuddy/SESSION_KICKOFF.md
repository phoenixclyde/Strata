# SESSION_KICKOFF.md ---- 新会话开场接手文本

> 用途：新开一个 WorkBuddy 会话、工作区指向 `D:/workbuddy_space/strata_ws/` 时，把下面横线之间的整段复制粘贴进去即可接手。
> 生成：2026-10-08 19:38 CST ｜ **刷新：2026-10-11 05:3x CST（W775delta 交接）**。

---

接手 Strata 项目（W775delta 之后）。工作区 `D:/workbuddy_space/strata_ws/`（独立工作区，已自包含，不需要 routeK 的东西）。

**第一动作**：按顺序读这五份，然后查技能清单
1. `PROJECT.md`（自包含入口：目录地图 / 服务 / 166 路径 / 固化通道 / 外部引用）
2. `.workbuddy/memory/MEMORY.md`（长期记忆，**3,000 字符注入窗**，现 2,898 chars 在窗内；见下方 TODOLIST 第 5 条）
3. `deploy/W750_MASTER_PLAN.md`（**唯一合并待办表**；§0.0 = 现时点执行版）
4. `deploy/W775_HANDOVER.md`（**运行期交接：§2 快照 / §4 未闭环 / §7 铁律 / §8 坑**）
5. `.workbuddy/memory/2026-10-11.md`（本日流水，含 W775delta + 审计段）

然后 Load 技能：凡涉及本项目操作（改参数、发车、审计、记忆压缩、交接），先加载对应技能再动手，不许凭印象直接改。

**项目现状（2026-10-11 05:3x）**
- **现役引擎/镜像/容器一律以 `deploy/W775_HANDOVER.md §2.2` 为准**（本件不再写死）。
  当前：引擎 **0.1.42**（md5 `5efa1d45c2e8c6f14b62a96b32d03155`）· 镜像 `strata-gfx906:0.1.42` · 容器 `strata166-407` @8090。
- 自启机制 = Docker 原生 `--restart unless-stopped`，**不用 systemd**。
- 模型 `qwen3.8-flash-next-ud-iq4_xs`；上下文 262144；KV 用 `--kv k8v4`。
- 远端测试台 166 = `192.168.50.166`，部署根 `/home/albus/strata166/`；生产 config md5 **`ff8cb97379f0bdbe76ee555da6d8729c`**（**2026-10-11 17:37 W4x-B7 固化**：`--resident-experts` 取代 `--resident-budget-gib`；旧 `6261ddf8a81bf0ebe90101d3b0cf8455`）。
- 现役参数：`--pcie-frac 0.20` / `--spec-min-p 0.70` / `--prompt-cache-every 8192` / `--conversation-cache-mib 4096` / `--mtp-window 8192`。
- 参数唯一真值：`deploy/params/PARAM_REGISTER.tsv`（**87 数据行 / ADOPTED 27 / REJECTED 46 / CANDIDATE 6 / REFERENCE 8**；**2026-10-11 20:1x 现算（第二轮收口）**（W4x-B7 的 `P09`->REJECTED、`P66`/`P65`->ADOPTED；W7W8 新增 `P72`；**status 收口把 7 项 CANDIDATE -> REJECTED**）；**引用前现算，别照抄**）。

**铁律**
- 引用任何性能读数**必须带 `Z0=off`**（省电档），否则与历史读数不可比。定义见 `.workbuddy/memory/2026-10-07.md`。
- 改参数唯一通道：register -> `gen_config.py --write` -> 推 166 -> `docker restart -t 30 <现役容器>` -> `verify_config.py` 须 FAIL=0。
- 交付件须 `CR=0` 且无禁用码位（`U+21D2`/`U+2192`/`U+2014`/`U+2013`/`U+2026`/`U+2265`/`U+2264`/`U+2260`/`U+2212`/`U+00D7`/`U+2605`）。
- 查容器内文件走 `docker exec`（宿主路径会假阴性）；只读探针也要落盘 + `python -u` + 每步时间戳 + 断言 rc。
- **不要用文件展示工具（present_files）**，交付物只在正文里给路径。
- 历史件里的 `D:/strata166/`、`D:/workbuddy/_z_rk81/` 是迁移前路径，**逐字保留未改**（是证据），换算见 `MAP_OLD_TO_NEW.md`。
- **发给外部的内容（含 GitHub PR/issue/回帖）先给机主过目**。

**待办（截至 2026-10-11，详见 `deploy/W775_HANDOVER.md §4`）**
1. ~~**W12 D 臂**（A 基线 / D=P59+P60）x decode `ms/step` x 5 runs~~ **[已完成 2026-10-11 11:39 收车：exact but no gain；`P59`/`P60` -> REJECTED，见 `W775delta_W12D_RESULT.md`]**
2. ~~**W12 k8v4 补产物**：重跑 `bash /home/albus/strata166/_w775_w12.sh B k8v4`~~ **[已完成 2026-10-11 11:50（B2 落账）]**
3. ~~**W13 读上游**：`expert_cache.hpp:11` 提到的 R4.1 LFU-decay vs LRU sweep 是否已有实现~~ **[已完成：`W775delta_W13_RESULT.md` ---- 引擎现役 `it never evicts`；离线复放 fill-only 0.7086 / LRU 0.9751 / oracle 0.9890（slots=9761）]**
4. ~~**W6 §4 族其余**（`P41`）~~ **[已判完 2026-10-11 19:3x：先测 3 个 = 2 实测无增益 + 1（`ATTN_LANECELL`）源码判定不发车]** · ~~**W7** `--lookup-chain`（`P42`）~~ **[已判 2026-10-11 19:4x：`--suffix-draft` 默认已开；`--lookup-chain K<=2` 空操作 => 不发车]** · ~~**W8** `kShape`~~ **[已判：编译期常量，非旋钮 => 新增 `P72` = REFERENCE]** · **余：W4**（逐桶账，只读，需先摸钩子）· **W9**（并发吞吐 `P97`，前提待重议）· **W20**（EXT 清单 13 行逐项复核，触发条件 17:37 已兑现）· **W11** 上游跟进。
5. ~~**`MEMORY.md` 超窗**（现 4,2xx B > 3,000 字符）=> 开工第一件事应走 `routek-memory-slim` 技能压回窗内。~~ **[AUDIT5-A3 更正 2026-10-11 19:xx]** 本项**已失效**：`MEMORY.md` 实测 **2,900 chars**（在注入窗内，与上方第 2 条一致）；无需压缩。
6. **[X] 先别动**：`P55`/`P56` 在 `k8v4` 下**主模型路径不可达**，别再发四臂空跑车（W774 已踩过一次）。

**外部（未迁，原地）**：`D:/Strata/` = 11.2 GB Windows 端可运行部署包，机主令留原地。
