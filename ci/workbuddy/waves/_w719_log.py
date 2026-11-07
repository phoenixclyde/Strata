# -*- coding: utf-8 -*-
import io, hashlib
P = r'D:/workbuddy/.workbuddy/memory/2026-10-08.md'
TXT = """

## W708 ---- Strata v0.1.40.2 三臂 bench + 官方 release note 逐条核对 + 上游 PR #1396

机主令：「仅针对这个新版本做一次bench，我看一下数据，审计。然后能建pr的建个pr给上游」，
并追问「v0.1.40.2 具体快在哪（对 0.1.40，官方交错对拍中位数）……你去github拉了这几版信息没有！」

### bench（三臂 ABBA，同一份 config，唯一有意的变量 = 引擎版本）
- A=`strata166-402`(0.1.40.2) / B=`strata166-401`(0.1.40.1) / C=`strata166-402` 复测；
  config `/data/strata-ud-iq4_xs.json`（UD-IQ4_XS / 262144 / k8v4 / spec4 / mtp / budget 76）。
- 预填中位 **455.8 / 456.4 / 456.0** tok/s；解码中位 **44.10 / 43.80 / 43.04** tok/s。
- 臂间差 <=1.74%，而**同臂内极差 11.6~13.0%** => **本机无分辨率内的差异**。
- 解释（主）：官方对同形态给出的**默认**增益量级只有解码 +1.7~4.3%（RTX3060/5070/P100）< 本机分辨力；
  多卡/低RAM/pin=/GUMBEL/hipBLASLt 全不适用本机。`STRATA_MMVQ_IL` 官方只说 RTX30+ 默认，**本机是否命中未验**。
- **[!] 本机不是"全常驻"这句话不能再说**：日志无"专家总量"读数；`24576 slots`/`32.24 GiB` 出自**较早一次
  `131072/int8` 启动块**（日志跨配置 append）。只能说到"**不是低 RAM 形态**"（RAM 侧 32.24~33.45 GiB、解码命中 94.6~96.4%）。

### 官方 release note（终于去拉了 —— 前一轮只取了元数据没取正文）
- 落盘 `D:/strata166/upstream/relnotes/v0.1.40{,.1,.2}.md`（经 `releases?per_page=8`；`/releases/tags/<tag>` 三次全 504）。
- 机主列的 6 条**逐字核对**：5 条（RTX30/50+P100 解码、layer-split +60%、低RAM +20~42%、pin=N 0.35~0.55s、
  GUMBEL +5.7~9% / 7900XTX hipBLASLt +32%）**全部在原文里**；第 6 条 `STRATA_GR_SPLIT=1` ——
  **内容对（K-split down、~3%/window、默认关因求和次序不同），但"新收编"不成立**：0.1.40.1 已有，
  8 篇 note 全文 0 命中该字样，`docs/AMD_HIP.md` 该行两版逐字相同。

### PR #1396（新建）
- fork `phoenixclyde/Strata`（API POST /forks，202 后 6s 就绪）-> 分支 `gfx906-build-fixes-402` @ `87c6d0218d`
  -> PR base `Niko1221:main` @ `e8ca9afd03d8`（== tag v0.1.40.2）**2 files +3/-2 / 1 commit**。
- 内容 = H5（`CMakeLists.txt` q6_k 实例门加 `OR STRATA_HIP_GFX906`）+ H6（gfx906 头补 `cudaEventBlockingSync` 映射）。
- **H5 必要性已直证**：移除 `mmq-instance-q6_k.cu.o` 后按**原链接命令行**重链 => `undefined symbol mul_mat_q_case<(ggml_type)14>`、
  `link_rc=1`、无产物；对照原归档 `link_rc=0` / 24,862,088 B。（`libstrata_mmq.a` 内 U=1 / W=1；其它 6 个归档定义数全 0。）
- 与已有 open PR 无重叠：`main` 的 **gfx906 头**里该宏 0 次；wave32 头本来就有；#1101 是往 **wave32 头**再加一次。
- **教训**：`_pr120_open.py` 建 PR 前**没查重**（不幂等），下次必须加 `?head=...&state=all`。

### [!][!] 两个方法学教训（本轮最值钱）
1. **判"两版本某文件差异"必须取未被任何人改过的原始产物**：我第一版拿 `tmp/src401` + `tmp/src401_pristine`
   做对比，**两棵树都跑过我们的补丁器**（都含我们写的 `// no q8_1 either; ...`），于是得出"只差注释"的**错结论**。
   改用 release **zip** 取原文（md5 自证：0.1.40.1 `ab856a50…` vs 0.1.40.2 `640fe793…`）才看清真相：
   0.1.40.1 L1743 是**裸 `return;`**，0.1.40.2 改成 `return false;   // the gfx906 STRATA_GR_SPLIT read...`
   => 这是 **#1083 第 1 项被上游采纳的代码修复**，也正是补丁器 v2 锚点失配的真因。**被 W708b 审计抓出（P1）。**
2. **162 上 clone 大仓会慢到像卡死**：`git clone --depth 1` 这个仓跑了约 5 分钟（16.8 MB pack），
   期间我误判"卡死"。且**本机 ssh 调用被中断会让远端脚本吃 SIGHUP 死掉**（clone 完成后续步骤全没跑）。
   => 远端长任务一律 `setsid nohup ... > log 2>&1 < /dev/null &`，再轮询日志（本项目 `T317` 同族）。

### 审计（W708b）
- 派独立只读 Explore 子 agent；结论 **1 P1 事实错误 + 1 P1 无证据 + 11 P2**，**主结论（无差异）成立**。
- 13 条已**全部**合并进 `D:/strata166/W708_STRATA402_BENCH.md` §8（该件重写，最终 16,666 B / `2da507cd…`）。

### 产物
- `D:/strata166/W708_STRATA402_BENCH.md`（主报告，含 §8 审计裁定）
- `D:/strata166/pr/PR_BODY.md` · `pr/pr_result.json` · `upstream/relnotes/*.md`
- 探针：`D:/workbuddy/_z_rk81/_pr108~_pr121*`、`remote/_h5v.sh`、`remote/_mkpr.sh`、`remote/_explog.sh`
- 166：`/home/albus/strata166/pr/`（`_mkpr.log`、`strata-fork`）
"""
b = TXT.encode('utf-8')
with open(P, 'ab') as f:
    f.write(b)
bb = open(P, 'rb').read()
print('appended %d B -> total %d B  CR=%d' % (len(b), len(bb), bb.count(b'\r')))
print('md5 =', hashlib.md5(bb).hexdigest())
