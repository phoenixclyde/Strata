# Strata 长期记忆（D:/workbuddy_space/strata_ws）
> 窗 <=3000；上游 `Niko1221/Strata`；部署 166 `/home/albus/strata166/`。
> 2026-10-08 自 routeK 工作区迁出。改本件前先归档到 `.workbuddy/memory/_bak/`。

## 0 定位与权威件
- 本工作区 = Strata 引擎在 gfx906（MI50 32GB）上的部署 + 参数调优。`deploy/` · `waves/`。
- 生产：**`strata-gfx906:0.1.41` / `strata166-405`** / 8090 / `--restart unless-stopped`（不用 systemd）；补丁面**归零**。
  切换/回滚：`bash /home/albus/strata166/w712/switch_strata.sh <新容器>`（旧容器自动探测 + 自动回滚）。
- 模型 `qwen3.8-flash-next-ud-iq4_xs`，上下文 262144，`--kv k8v4`。
- 权威件：`PARAM_REGISTER.tsv`（参数唯一真值）· `W713_PLAN.md`（方案 + 全量账）· `W713_UPGRADE.md` · `W713_AUDIT{,2}.md`。
- 外部未迁（原地）：`D:/Strata/`（11.2GB Windows 部署包）。

## 1 铁律与通道
- **改参数唯一合法通道**：改 register -> `gen_config.py --write` -> **推 166 `params/`** -> restart -> `verify_config.py` FAIL=0。
  **漏推 166 会让"本机==166"变成假陈述**（2026-10-08 第二轮审计 P0 实证）=> 改完 register 必须两侧 `md5sum` 对比。
- **容器名/版本/指纹一律写指针、不写字面值**（本次两次切换 + 三次改 register 各暴露一处过期副本）。
- **引用任何性能读数必须声明 `Z0=off`**（省电档，见 `2026-10-07.md` W706）。
- 交付件禁用码位（U+21D2/2192/2014/2013/2026/2265/2264/2260/2212/00D7），须 CR=0。
- 查容器内文件走 `docker exec`（宿主路径假阴性）；只读探针也要落盘 + `python -u` + 时间戳 + 断言 rc。
- 本机 shim 会把 `/data/x.py` 这类参数转成 Windows 路径 => 驱动只传短记号。脚本里**别用 ASCII 双引号包中文串**（两次语法自伤）。
- 改既有长件前**先备份该件本身**（曾用"截断到标题再续写"误删 `W713_PLAN` §6 整节）。
- 改本件：先归档 -> 五断言（CR=0 / chars<=2900 / BAN=0 / 结尾换行 / 读回相等）-> 落盘 -> 报数六件。

## 2 现役参数（ADOPTED 三项）
`--pcie-frac 0.20` · `--spec-min-p 0.70` · `--prompt-cache-every 8192`（温 TTFT 23.07 -> 5.86 s，**仅 8-16k 档受益**）。
实测否决：`--prompt-cache-tail`（无增量）· `every 4096`（reused=0）· `--pool-workers` 改非默认。
LIVE config md5 `d2b10f0c4e8293ba010614c7acc70bea`；register 35 行 / ADOPTED 16 / REJECTED 12 / CANDIDATE 7（**md5 每改必变，别抄**）。

## 3 机制（证据等级已分级）
- **「前缀须与 prefill chunk 整数倍对齐」是实测规律、非源码确证**（源码/help 无显式断言，且 `every=4096`+`chunk=8192` 得 `reused=0` 解释不通，**待追**）。
- 默认 16384 让 8k~16k 段完全没有多轮复用；`<8k` 任何值都 `reused=0`（短会话每轮整条重预填）；`>16k` 时 8192 与 16384 等效、32768 归零。
- **`--prefill` 是会改答案的旋钮**：`4096` 在 6,831-token 段上生成长度都变了 => **不改基线 P10**（收益 -70.6% 温 TTFT、代价 冷预填 -11~-23%，都不足以抵"答案会变"）。
- 分辨力：预填 1.2~1.7%，解码 9.5~15.0%（低于此不可判）。

## 4 待办（全量账见 `W713_PLAN.md` §6）
- **未做**：B7 新候选 P35 `STRATA_STAGER_SSD` · P31/P33 多轮缓存 · P23 `STRATA_PREFILL_CPU_SHARE`(+`_MAX=3072`) · P30 `STRATA_MMVQ_IL` 判定 · P29 GUMBEL · P28 GR_SPLIT · `--kv-grow` · C4 `_sshutil` 自包含缺口 · C5 避坑回写 · C3 清理（5 镜像 / 5 容器）· 向上游提 feature request（子 chunk 边界 checkpoint）。
- **重做**：0.1.41 的**解码**分母（闸门只覆盖预填/温 TTFT/reused）；0.1.40.1 时代读数仅存档。
- **不得引用**：`waves/_w727.out.txt`（测试域无效）。

## 5 上游与审计
- PR **#1396**（我们的 gfx906 构建修复）**已合并进 0.1.41** => 补丁面归零（H1~H6 上游全修），补丁器降级为纯验证/回归闸门（构建实测 `PATCH_SURFACE_ZERO`）。
- 2026-10-08 **两轮**独立对抗性审计：`W713_AUDIT.md`（6 条 P1）、`W713_AUDIT2.md`（含 register 真值分叉 P0、整节误删重建、口径混源）。
