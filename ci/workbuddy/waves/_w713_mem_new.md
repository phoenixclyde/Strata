# Strata 长期记忆（D:/workbuddy_space/strata_ws）
> 窗 <=3000；上游 `Niko1221/Strata`；部署 166 `/home/albus/strata166/`。
> 2026-10-08 自 routeK 工作区迁出。本版基线备份 = `.workbuddy/memory/_bak/MEMORY.md.bak_w713_*`。

## 0 定位与权威件
- 本工作区 = Strata 引擎在 gfx906（MI50 32GB）上的部署 + 参数调优。`deploy/` · `waves/`。
- 生产：`strata-gfx906:0.1.40.4` / 容器 `strata166-404` / 8090 / `--restart unless-stopped`（不用 systemd）；
  **0.1.41 镜像已建**（`c45268e786e1`，补丁面归零），**容器 -405 与切换未做**。
- 模型 `qwen3.8-flash-next-ud-iq4_xs`，上下文 262144，`--kv k8v4`。
- 权威件：`PARAM_REGISTER.tsv`（参数唯一真值）· `W713_PLAN.md`（现行方案 + 全量账）· `W712_UPGRADE.md`（升级自证）。
- 外部未迁（原地）：`D:/Strata/`（11.2GB Windows 部署包）。

## 1 铁律与通道
- **改参数唯一合法通道**：改 register -> `gen_config.py --write` -> 推 166 `params/generated/` 覆盖 LIVE -> `docker restart -t 30 <运行中的容器>` -> `verify_config.py` FAIL=0。
  **容器名不写死**：核验器自动探测运行中的容器（2026-10-08 审计 P1 修；原写死 `-402`，切 -404 后一直在 inspect 死容器）。
- **引用任何性能读数必须声明 `Z0=off`**（省电档，定义见记忆 `2026-10-07.md` W706）。
- 交付件禁用码位（U+21D2/2192/2014/2013/2026/2265/2264/2260/2212/00D7），须 CR=0。
- 查容器内文件走 `docker exec`（宿主路径假阴性）；只读探针也要落盘 + `python -u` + 每步时间戳 + 断言 rc。
- 本机 shim 会把 `/data/x.py` 这类参数转成 Windows 路径 => 驱动只传短记号，真实路径在脚本内拼。
- 取值型参数不能排在 args 末位（核验器按「下一个 token」判值）。
- 改本件前先归档备份；落盘前五断言（CR=0 / chars<=2900 / BAN=0 / 结尾换行 / 读回相等），报数六件。

## 2 现役参数（ADOPTED 三项）
`--pcie-frac 0.20` · `--spec-min-p 0.70` · `--prompt-cache-every 8192`（温 TTFT 23.07 -> 5.86 s，**仅 8-16k 档受益**）。
实测否决：`--prompt-cache-tail`（无增量）· `every 4096`（reused=0）· `--pool-workers` 改非默认。
LIVE config md5 `d2b10f0c4e8293ba010614c7acc70bea`；register md5 `3bf819e3ccd3f54ed454154b14c3eb3f` / 35 行 / ADOPTED 16 / REJECTED 12 / CANDIDATE 7。

## 3 机制（证据等级已分级）
- **「前缀须与 prefill chunk 整数倍对齐」是实测规律，不是源码确证**：B1 矩阵 + 4096 对照支持，但源码/help 无显式断言，且 `every=4096`+`chunk=8192` 得 `reused=0` 直读解释不通（**待追**）。
- 默认 16384 让 8k~16k 段完全没有多轮复用（B1 双向实测：8192 得 `reused=8192`、温 TTFT 5.87 s；16384 得 0、23.07 s）。
- B1 边界：`<8k` 任何值都 `reused=0`（短会话每轮整条重预填）；`>16k` 时 8192 与 16384 等效、32768 归零 => **8192 是三档都不劣的唯一档位**。
- B1b：`--prefill 4096`+`every 4096` 让 4.6k 会话温 TTFT 10.58 -> 3.59 s（-66%），代价冷预填 -11%；**未在 0.1.41 复核、答案是否变未测** => 未采纳。
- 分辨力：预填 1.2~1.7%，解码 9.5~15.0%（低于此的差异不可判）。

## 4 待办（全量账见 `W713_PLAN.md` §6）
- **未做**：切换 0.1.41 + 闸门脚本化 · B1b 收口三件 · 新候选 P35 `STRATA_STAGER_SSD` · P31/P33 多轮缓存 · P23 `STRATA_PREFILL_CPU_SHARE`(+`_MAX=3072`) · P30 `STRATA_MMVQ_IL` 判定 · P29 GUMBEL · P28 GR_SPLIT · `--kv-grow` · C4 `_sshutil` 自包含缺口 · C5 避坑回写 · C3 清理（5 镜像 / 4 容器）。
- **重做**：0.1.40.x 的全部读数须在 0.1.41 重取（#1353 / #1454 / tokenizer 缓存 三条都可能改数）。
- **不得引用**：`waves/_w727.out.txt`（测试域无效：6,833-token prompt 短于一个 chunk）。

## 5 上游与审计
- PR **#1396**（我们的 gfx906 构建修复）**已合并进 0.1.41** => **补丁面归零**（H1~H6 上游全修，H5/H6 即我们补丁原文）；补丁器 v3 降级为**纯验证 / 回归闸门**（构建实测 `PATCH_SURFACE_ZERO`）。
- 2026-10-08 三路对抗性审计：修掉核验器硬编码容器名等 6 条 P1（报告见 `deploy/`）。
