# W725 ---- 六项待办清扫（机主裁定后执行）

- 日期：2026-10-09 20:1x - 20:4x（本机时间）
- 缘起：机主对「还有待办吗」的清单逐条裁定：
  **一**：① 上游 PR **先等等、之后一并弄**；② P29 **据实判断**；③ C3 **可以清**
  **二**：vision 核验 + #1454 两条 **都做**
  **三**：① 0.1.40.x 重取 **别弄了**；② 审计残余 ③ mtp.cpp:428 ---- **你定**
- **本波六项全部收口**，其中**查出 1 处表述错误、1 处账本过期、1 处工具误置、1 处我自己的判据错**。

---

## 1 P29 `STRATA_SPEC_GUMBEL` -> **REJECTED**（据实判定）

**事实**：本服务**默认口径 = 贪心**（`server.py:576-577`："An absent temperature keeps the engine's
default, **which is greedy**"），且 config **无 `sampling` 段** => 该开关在当前用法下**恒为空操作**。

**判定**：`CANDIDATE -> REJECTED`。**与 P30 的区别**：P30 是引擎层**结构性不可达**（HIP 分支恒 false）；
P29 是**用法层未触发**，非缺陷。注记：若将来引入 `temperature>0` 用法，**直接设 `STRATA_SPEC_GUMBEL=1`
即可**（引擎侧无需任何改动），届时须单测（note 的 +5.7~9% 是 AMD 数据，未在我机验过）。

- register：**40 行 / ADOPTED 22 / REJECTED 17 / CANDIDATE 1**（仅剩 P33）；两侧 md5 一致 `6cf03586...`
- **config 未变**（`115bcee9...`，P29 本就不进 config）=> **无需重启**，服务零影响
- 本机核验器 **PASS=19 FAIL=0**

---

## 2 vision 段独立核验（完成；核验器 V00-V02 的 SKIP 缺口已补）

| 核验点 | 实测 |
|---|---|
| register V00/V01/V02 vs config `vision` 段 | **逐字一致**（exe/mmproj/model 三项） |
| 编码器 exe | `/data/vision/strata-vision` **7,754,632 B**，`-rwxr-xr-x`，sha256 `fadfa15a...` |
| mmproj | sha256 **`b1a82259...`** = register V01 声明值 = huihui 仓 oid |
| 编码器进程 | **pid 9 常驻**（etime 49:56），argv 含 `--mmproj ... --model ...` 与 config 一致 |
| `/v1/models` | `architecture.input_modalities = ["text","image"]`（`server.py:4554`：`if svc.vision is not None`）|
| `/v1/status` | **`"vision": {"enabled": true, "available": true, "error": null}`**（最强证据）|
| 端到端 | 自造 448x448 图（黑框+红圆+左下蓝矩形）-> 模型输出 **"红色圆形，位于中央 / 蓝色正方形，位于左下"**（准确）|

**一处我自己的判据错（如实记）**：第一版探针读 `m["input_modalities"]` 得 **None**，据此怀疑 W715 报告有误；
实为**层级读错** ---- 该字段在 `architecture` 嵌套内。**W715 的表述是对的，错在我的探针**。

---

## 3 #1454 与 tokenizer cache（0.1.41 两条未单测项）

### 3.1 `#1454` 省 320 MiB -> 走**源码算账**（收益远小于头条数字）

release note 原文：`Prompt buffers (#1454, #1465): the half output shares the embedding storage
(**320 MiB less at 32,768 rows**) ... Default answers are identical`。
源码（`prefill.cpp:252-256`）：`bo` 复用 `emb` 存储，**每个 chunk 省 `T * N` floats**；默认 **planner 仍把它计入**
（故 0.1.40.3 的 chunk 与借槽数不变），`STRATA_EMB_REUSE_ACCOUNT=1` 才让 planner 用上（**会改 prompt rounding**）。

**算账**：`N = 2560`（由 pack `index.txt` 的 `output.weight ... 2560 248320` **实证**）；
我们的 chunk = **8192**（引擎日志 `prompt chunk auto: 8192 tokens, a 96-slot ring`）。

```
32768 x 2560 x 4 B = 335.5 MB = 320 MiB   <- 与官方数字严丝合缝
 8192 x 2560 x 4 B =  83.9 MB =  80 MiB   <- 我们的实际量
80 MiB / 2.30 MiB per slot ~ 35 slots (+0.36%)   <- 远低于分辨力
```

=> **默认白得约 80 MiB（约 +35 槽 / +0.36%），在分辨力下**；`STRATA_EMB_REUSE_ACCOUNT=1` **不采纳**
（会改 prompt rounding，与保位一致原则冲突）。

### 3.2 tokenizer cache -> **隔离实测**（不掺引擎）

实现（`tools/strata_tokenizer.py:211-233`）：piece 级 `_piece_ids` 缓存，`PIECE_CACHE_MAX = 200_000`，
注释原文动机 = *"an agent resends its whole history every turn"*。

**实测**（容器内直接调 tokenizer，`/data/packs/huihui-ud-iq4_xs/tokenizer`）：

| 臂 | 耗时 | 说明 |
|---|---|---|
| 冷（新实例，空 piece cache） | **0.109 s** | 105,826 tokens / 94,220 pieces |
| 热（同实例重发） | **0.054 s** | **-50.5%**，且 **ids 完全一致**（"the same ids"）|
| 追加式（前缀 + 一句） | 0.054 s | 前缀 pieces 全命中 |
| 对照（未入缓存的倒序文本） | 0.120 s | 约等于冷 => **证明收益确来自 piece 缓存** |

=> **默认生效、白得**；量级 = 每次重发省约 **0.055 s**。（官方口径 89K tokens 0.32->0.07 s 为不同机器/版本）

---

## 4 C3 旧镜像/容器清理（**已执行**；真账与头条差 15 倍）

### 4.1 边界：166 是**共享机**，只动 Strata 域

50 个容器里大量是 **routeK 项目**（`rk_w680_*` / `rk_w646_*` / `w642*` ...）与**服务**
（open-webui / netdata / comfyui-cu130 / portainer / searxng）=> **一律不碰**。

### 4.2 真账（layer 级 + UNIQUE SIZE）

| 对象 | 名义 SIZE | **UNIQUE SIZE** |
|---|---|---|
| `strata-gfx906:0.1.41` | 6.57 GB | 483.6 MB（**保留**）|
| `0.1.40.4` | 6.57 GB | 480.2 MB |
| `0.1.40.2` | 6.57 GB | 480.2 MB |
| `0.1.40.1` | 6.55 GB | 460.1 MB |
| `0.1.39` | 6.52 GB | 839.7 MB |
| **五张合计** | **32.8 GB** | **约 2.74 GB** |

=> **docker 头条报 `Images RECLAIMABLE 46.17GB`，虚高约 15 倍**（差额是**与别的项目共享的层**）。
层集合运算：`kept_layers=240`（所有有容器引用的镜像）、`候选=0`（5 张 strata 镜像**当时都还有容器**）。

### 4.3 执行（带守卫）

守卫：① 待删镜像与**运行中**容器的 image id 交集为空；② 待删容器状态全部非 running（实测 5 个均 `exited`）。

```
docker rm strata166-405 strata166-404 strata166-402 strata166-401 strata166
docker rmi strata-gfx906:0.1.40.4 strata-gfx906:0.1.40.2 strata-gfx906:0.1.40.1 strata-gfx906:0.1.39
docker builder prune -f
```

**结果**：容器 50 -> 45、镜像 46 -> 42、**`df -h /` 774G -> 771G（释放 3 GB）**、Build Cache 2.521GB -> **0**。
Strata 域终态：**`-407`（Up）/ `-406`（回滚位）/ `0.1.41`**；服务 HTTP **200**。

### 4.4 **实战复现了技能记过的坑**：删镜像不释放

删完镜像后 `df -h /` **一点没变**（774G），而 **Build Cache 从 260.7MB 跳到 2.521GB**（同一批字节被 buildkit
**重归类**）。必须 `docker builder prune -f` 才真回收。=> **技能 `docker-disk-truth` W646 的判据再次验证。**

### 4.5 删前**账本引用检查**救了一次（技能 W646b 硬要求）

`deploy/configs/workbuddy-strata166.md:6` 把回滚写成 `docker start **strata166-402**` => **-402 是登记在册的回滚目标**。
=> 先**修账本**再删：该文档（W712 时代视图）已更新 8 处（现役 `-406`->`-407`、回滚位 `-406`、
`:59` 的"回滚到 0.1.40.2"标注**作废**），删后 `start strata166-402` **不再残留**。

### 4.6 顺带清掉**误推/过期工具副本**

`166:/home/albus/strata166/params/` 里有 `gen_config.py`（Oct 8 02:56 旧版）、`verify_config.py`（同）、
以及**我误推的** `_sshutil.py`。三者**在 166 上都跑不通**（`_sshutil.py` 硬编码 Windows 的
`C:/Program Files/Git/usr/bin/ssh.exe`）=> **已全部删除**，`params/` 只剩 `PARAM_REGISTER.tsv`（数据）+ 备份。

> **我自己的判据错（如实记）**：我一度在 **166 上**跑 `verify_config.py` 并据此报"166 缺 `_sshutil`"。
> **真相：`verify_config.py` 是**本机工具**（它 ssh 到 166），**不该在 166 上跑**。本机跑 = **PASS=19 FAIL=0**。

---

## 5 审计残余（两项可做的都做了）

### 5.1 PR #1396 溯源 -> **查出一处表述错误（重要）**

实查 GitHub API：

```
number 1396   title "hip/gfx906: the tree does not build (q6_k MMQ instance and cudaEventBlockingSync)"
state **closed**   merged **False**   user phoenixclyde
head phoenixclyde:gfx906-build-fixes-402 @ 87c6d021...
```

维护者 `Niko1221` 的评论原文（2026-10-08T12:18:03Z）：

> "Thanks @phoenixclyde. The gfx906 build fix (the q6_k MMQ instance and cudaEventBlockingSync) **is in 0.1.41
> with your authorship kept**. We have no gfx906 card to run it on, so it is checked by compiling only.
> **Closing as ported.**"

=> **真相**：修复**确实进了 0.1.41**，且**保留我们的作者署名**（落地 commit = `a732a19b6f`，在 main 上，
改的正是 `CMakeLists.txt` 与 `strata_hip.h` 两个文件）；但**PR 状态是 `closed`（非 `merged`）**。

**更正**：此前记的"PR #1396 **已并入** 0.1.41" => 应表述为
**"已 ported 进 0.1.41（维护者自杀 commit，保留作者署名），PR 状态为 closed-not-merged"**。
（差别重要：若有人去 GitHub 看 PR 状态，会看到 `closed / merged: False`，可能误判"未被采纳"。）

### 5.2 166 侧下载来源 -> 查清 + **意外发现 PR 通道早已打通**

- 源码包位置：**`/home/albus/strata166/build-ctx-411/transfer/`**（`strata-src-0.1.41.zip` 19.0 MB、
  `llama.cpp-3cf0325.tar.gz` 34.6 MB）；**166 侧无独立 `.sha256` 记录**（校验靠旧波次"两侧各自下载后对哈希"）。
- **重大发现**：`/home/albus/strata166/pr/` 是**上次提 PR 的完整工作区**，含
  **`strata-fork/`（真 git 仓，remote = `git@github.com:phoenixclyde/Strata.git`）** +
  **`_mkpr.sh`（7 步提 PR 流程）** + `commitmsg.txt`。

=> **W724 说的"缺 git 通道"其实早已打通** ---- 提上游 PR **不需要新配任何东西**，复用该 fork 即可
（结论已回写 W724 报告）。

---

## 6 `mtp.cpp:428` 同型判定 -> **不是漏判**（我的初始猜测被推翻）

`:420` 与 `:428` **相隔 9 行、判据不同**，我一度判它是"同型漏判"。**查完使用点，结论相反**：

```cpp
:428  #if !defined(STRATA_USE_HIP)                    // 非 HIP（含 gfx906）=> 创建 side_
:430      cudaStreamCreateWithFlags(&side_, ...); cudaEventCreateWithFlags(&sh_fork_/&sh_join_, ...);
:864  #if defined(STRATA_USE_HIP)  /  :865  return false;   // HIP => 关分支（**W735 更正**行号：862 是注释行，原写 862）
:866  #else  getenv("STRATA_MTP_SHARED_BRANCH") 默认 true   // 非 HIP（含 gfx906）=> 用 side_
```

=> **创建与使用用同一个宏、配套一致 => 自洽，不会崩。**（若按我的猜测去"补 `&& !defined(STRATA_HIP_GFX906)`"，
会**只关创建、不关使用** => 反而引入 `side_ == nullptr` 的**真 bug**。）**=> 此路不可走，如实记录。**

**但留了一条真问题**：注释（`:861`）与头文件（`mtp.hpp:226`）都写 **"(CUDA)"**，而 gfx906 上该分支**实际默认开**
=> **行为与注释/意图不符**，属上游**第 3 处宏判据不一致**（`:420` 认 gfx906，`:428/:864` 不认；W735 更正行号）。
**其性能/正确性影响未实测 => 不能凭源码断言**，列为"若要动 MTP 时再单测"的候选。

---

## 7 落账与落盘

| 件 | 变动 |
|---|---|
| `deploy/params/PARAM_REGISTER.tsv` | P29 `CANDIDATE -> REJECTED`；分布 **22/17/1**；两侧 md5 `6cf03586...`；备份 `.bak_w725_*` |
| `deploy/params/generated/strata-huihui-ud-iq4_xs.json` | **未变**（`115bcee9...`）|
| `deploy/configs/workbuddy-strata166.md` | 8 处更新（现役/回滚/作废标注 + 过期声明）；备份 `.bak_w725_*` |
| `166: params/` | 删掉 3 个跑不通的 `.py` 副本 + `__pycache__` |
| `166: 容器/镜像` | 删 5 容器 + 4 镜像 + builder prune => 释放 **3 GB** |
| `deploy/W724_UPSTREAM_PR.md` | 补 §9（PR 通道已打通 + PR #1396 真相）|
| 本波报告 | `deploy/W725_SWEEP.md`（本件）|

**待办变动**：`#5 P29` 关、`#12 vision 核验` 关、`#7 #1454 两条` 关、`#10 C3` 关、
`#4 审计残余` 两项可做的已做（C-530 中位数按「0.1.40.x 别弄了」不做）、`mtp.cpp:428` 判完（自洽）。
=> 全量账 §6.2 的"剩 5 项"中，**4 项本波关闭**，仅剩 `#11 上游`（机主令"先等等"）。

> 过程脚本：`C:\Users\clyde\AppData\Local\Temp\_w725*.py`；原始输出 `_w725*.txt`。
> 166 侧临时文件（`/tmp/_d2s.json`、`/tmp/tokbench.py`）已清；`/tmp` 里其它 `_*` 属别的项目，**未动**。
