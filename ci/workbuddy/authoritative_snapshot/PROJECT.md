# Strata 工作区（gfx906 / MI50）

自包含工作区。2026-10-08 由 routeK 工作区（`D:/workbuddy/`）迁出，机主令「交接 strata 部分去一个新的工作区」。
**打开本目录即可独立开工，不需要 routeK 工作区的东西。**

---

## 一、目录地图

| 目录 | 内容 | 来自 |
|---|---|---|
| `deploy/` | 部署件与交付件：6 份 `W7xx` 报告 · `params/`（register + 生成器 + 核验器 + 证据）· `docker/`（Dockerfile + 补丁器）· `data/`（探针）· `pr/` · `configs/` · `scripts/` · `systemd/` · `logs/` · `tmp/` · `transfer/` · `weights/` · `upstream/` | 原 `D:/strata166/` |
| `waves/` | 波次驱动与原始输出：`_pr81`~`_pr134`（构建/PR 波）· `_w717`~`_w748`（参数波）· `_gh.py`（GitHub 通道）· `_strata_envs.json` | 原 `D:/workbuddy/_z_rk81/` |
| `.workbuddy/memory/` | 本工作区记忆：`MEMORY.md`（长期）· `2026-10-07.md`（166 Z0 基线）· `2026-10-08.md`（W707~W709e 全文） | routeK 工作区记忆 |
| `tools/` | `_verify_copy.py`（迁入校验器，逐文件 md5） | 本次新建 |
| `MAP_OLD_TO_NEW.md` | 旧路径 -> 新路径映射（**引用历史件前先看这张表**） | 本次新建 |

---

## 二、现役服务

| 项 | 值 |
|---|---|
| 引擎 | Strata `v0.1.41`（上游 `Niko1221/Strata`；2026-10-08 连升两次：0.1.40.2`->`0.1.40.4 见 `deploy/W712_UPGRADE.md`，0.1.40.4`->`0.1.41 见 `deploy/W713_UPGRADE.md`） |
| 镜像 | `strata-gfx906:0.1.41`（`c45268e786e1` / 6.57 GB；补丁面归零） |
| 容器 | `strata166-406`（端口 **8090**，`--restart unless-stopped`） |
| 回滚 | 旧容器 `strata166-402`（0.1.40.2）/ `-401`（0.1.40.1）/ `strata166`（0.1.39）均在，`Exited`；`bash /home/albus/strata166/w712/switch_strata.sh strata166-404`（通用切换脚本自带停旧/起新/轮询/回滚；`-404`=0.1.40.4、`-402`=0.1.40.2 均 Exited 保留） |
| 自启机制 | **Docker 原生 restart policy**，不用 systemd（166 上 6 个常驻容器全走这个） |
| 模型 ID | `qwen3.8-flash-next-ud-iq4_xs` |
| Base URL | `http://192.168.50.166:8090/v1` |
| 上下文 | 262144（输入 229376 + 输出 32768）；KV 用 `--kv k8v4` |
| 冷启动到可用 | 约 20 秒（页缓存热）~ 240 秒（冷） |

一行自检（接入前先跑，两条都 200 再谈别的）：

```bash
curl -s http://192.168.50.166:8090/v1/models
curl -s http://192.168.50.166:8090/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"model":"qwen3.8-flash-next-ud-iq4_xs","messages":[{"role":"user","content":"Reply OK"}],"max_tokens":16}'
```

> 166 是测试台，会被关机；**无远程唤醒**，重启要现场按电源键（起来后容器自启）。
> 服务**无鉴权**，同网任何人可用；要收口就在 `deploy/params/generated/strata-ud-iq4_xs.json` 加 `"api_key"`。

---

## 三、远端 166 路径（未迁，服务端）

| 路径 | 内容 |
|---|---|
| `/home/albus/strata166/` | 部署根（与本地 `deploy/` 同构） |
| `/home/albus/strata166/data/strata-ud-iq4_xs.json` | **LIVE config**（当前 md5 `69aa8607bd0a58dc79466b1b71d6a4f9`；2026-10-08 因 `--native` 改指 /models 而变化） |
| `/home/albus/strata166/params/` | register / 生成器 / 核验器（与本地两机同步） |
| `/home/albus/strata166/w709/` | 校准窗口脚本（`run_calib.sh` / `watchdog2.sh`） |
| `/home/albus/strata166/build-ctx-402/` | 0.1.40.2 构建上下文（历史） |
| `/models/unsloth/Qwen3.8-Flash-Next-UD-IQ4_XS/` | **模型权重（2026-10-08 起）**：3 分片 + `mmproj-Qwen3.8-Flash-Next-BF16.gguf`；容器挂 `/models:ro`；`/home/albus/strata166/weights` 现为指向此处的符号链接（保旧容器回滚） |

---

## 四、改参数的唯一合法通道

```
改 deploy/params/PARAM_REGISTER.tsv 的 status/value
  -> python deploy/params/gen_config.py --write          # 产出生产 config，禁止手改 config
  -> 推到 166 的 params/generated/，再覆盖 data/ 的 LIVE（属主是 root 时用 sudo -n）
  -> docker restart -t 30 <现役容器，见 §二>
  -> python deploy/params/verify_config.py               # 四数据面复验，必须 FAIL=0
```

`verify_config.py` 会读 register 的 ADOPTED 行 => 改了 register 就得重新生成，否则复验会红。

---

## 五、环境声明（引用读数前必读）

**`Z0 = off`（省电档）**：GPU `perflevel=auto` / CPU `governor=schedutil` / THP `madvise`。
**引用任何性能读数必须带这条**，否则与历史读数不可比。定义与复归方法见 `.workbuddy/memory/2026-10-07.md`。

---

## 六、外部引用（在工作区之外，原地未迁）

| 路径 | 内容 | 说明 |
|---|---|---|
| `D:/Strata/` | Windows 端可运行的 Strata 部署包：`engine/`（ROCm DLL + `strata.exe`）· `pkg/`（`strata.exe` / `strata-vision.exe`）· `src/`（`Strata-0.1.39` 源码树）· `strata-windows-x64*.zip` + 分卷 | 11.2 GB / 7194 文件，**机主令留在原地**。若 Windows 侧有快捷方式指向 `D:\Strata\engine\strata.exe`，它仍然有效 |
| `C:/Users/clyde/.workbuddy/skills/flashnext-engine-selection/` | 引擎选型与 gfx906 落地技能（含 Strata 章节） | 用户级技能，跨工作区自动可用 |
| `D:/workbuddy/_z_tools/mem_slim.py` | 记忆压缩唯一入口（配合 `routek-memory-slim` 技能） | 留在 routeK 工作区，需要时按路径取 |
| ~~`D:/strata166/`~~ · ~~`D:/workbuddy/_z_rk81/`~~ | 迁移前的部署件 / 波次件 | **已于 2026-10-08 删除**（机主批准；删前逐文件校验"源 ⊆ 目标"，两个白名单件已快照）。历史件里的旧路径**逐字保留不改**，换算与证据见 `MAP_OLD_TO_NEW.md` 第六节 |

---

## 七、下一步

1. 按 `deploy/W709_HANDOVER.md` §3/§4 续接：**五项未测参数**（含各自测量配方）+ 补 P34 的 `>16k` / `<8k` 两档。
2. 重跑**独立对抗性审计**（上一轮子 agent 通道 3 次被 killed，只做到机械化证据链审计 35/36，强度上限已声明）。
3. 改参数**只走**第四节那条通道。
4. 可选清理：旧镜像 `strata-gfx906:0.1.39` / `0.1.40.1`，旧容器 `strata166-401` / `strata166`（现为 `Exited`，保留用于回滚）。
