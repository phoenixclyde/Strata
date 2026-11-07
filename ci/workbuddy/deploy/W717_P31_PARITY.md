# W717 ---- P31 终审（上游 parity）+ 工具件自包含

- 日期：2026-10-09 19:0x - 19:1x（本机时间）
- 机主令：「继续。同步看一下上游没有更新」
- **结论先说**：① 上游**无更新**（最新仍是 v0.1.41）；② P31 `--conversation-cache-mib` 的
  「答案一致性」悬案**已解** ---- 上游 parity 工具给出 `PASS`，**主模型状态逐字节一致**，
  故已**采纳进生产**（value 1024 -> 4096，容器 `-407` 已重启，`verify_config.py` **PASS=18 FAIL=0**）；
  ③ 顺手关掉 C4 / C5 两项工具件欠账，并在 C4 中**发现并修掉一个真 bug**。

---

## 0 上游核查：无更新

| 项 | 值 |
|---|---|
| 最新 release | **v0.1.41**，published `2026-10-08T12:14:59Z`（= 北京 10-08 20:14） |
| 最新 commit | `fb58e0dbc8`（2026-10-08T10:25:39Z）= **v0.1.41 这个 tag 指向的 commit** |
| repo `pushed_at` | `2026-10-08T12:14:59Z` ---- 与 v0.1.41 发布**同一时刻**，即此后 main 无新提交 |
| tags 面 | v0.1.41 仍是最高 tag（v0.1.40.4 / .3 / .2 / .1 / .40 ... 依次向下） |
| 判定 | **我们已是上游最新**（生产 `strata-gfx906:0.1.41`） |

> 注：repo `updated_at` = 2026-10-09T10:56Z，那是仓库元数据（star 等）刷新，**不是代码推送**；
> 判据要用 `pushed_at` + 最新 commit 日期，不能看 `updated_at`。

---

## 1 P31 终审：答案一致性 = 逐字节一致

### 1.1 为什么必须用上游工具，而不是"再跑一次我的探针"

W713 B3 的**未决**是：两臂出现「同一内容在不同臂给出不同 md5」且呈**互换**模式，
当时无法排除两件事 ---- (a) 我的探针把两会话输出串位；(b) 该路径确有非确定性。
「换 md5」这种判据本身也已被 W716 证明不可靠（本机**贪心不等于可重复**）。
上游 `tools/conversation_cache_parity.py` 正好为此而设：它比的是**引擎内部状态指纹**
（`STRATA_STATE_HASH=1`），不是输出文本 md5。

### 1.2 跑法

| 项 | 值 |
|---|---|
| 工具 | `/src/tools/conversation_cache_parity.py`（253 行，上游 0.1.41 自带；**默认 dry-run**） |
| 场景 | `--scenario reuse`（A/B/A 输出 + checkpoint 复用 + 状态指纹） |
| 参数 | `--config /data/strata-huihui-ud-iq4_xs.json --engine /src/build-906/strata --output <新目录> --cache-mib 4096 --spec 1 --run` |
| 臂 | **baseline**（`--conversation-cache-mib 0`）vs **candidate**（`4096`），**串行**各起一次私有引擎 |
| 执行环境 | **临时容器** `strata-parity`（与生产同设备同挂载；`--entrypoint bash`）；`/src` 等只在容器内存在 |
| 独占窗口 | 停 `-407`（显存 99.1% -> 10 MB 释放干净），跑完立即 `docker start strata166-407` 拉回 |
| 耗时 | 约 4 分 7 秒（19:01:56 起 ---- 19:06 出 PASS），2 次引擎加载各约 2 分钟 |

序列（工具内建）：`A`(1 tok) -> `B`(1 tok，无关会话) -> `A+`(2 tok，A 的续写) -> `B-again` -> `A+-checkpoint`。

### 1.3 结果：`PASS`

工具原话：

```
PASS: A/B/A output and checkpoint reuse, byte-exact main-model state
```

**输出一致性**（工具断言，三次比较全 True）：

| 比较 | ids 相同 | 状态相同 |
|---|---|---|
| baseline `A+` vs candidate `A+-checkpoint` | **True** | **True** |
| candidate `A+`（restore 后） vs candidate `A+-checkpoint` | **True** | **True** |

**checkpoint 复用确实发生**（candidate 侧 `reused`）：

| 记录 | gen tokens | reused |
|---|---|---|
| `A` | 1 | 0 |
| `B` | 1 | 0 |
| `A+` | 2 | **1957**（= A 的 prompt 全长） |
| `B-again` | 1 | **1952** |
| `A+-checkpoint` | 2 | **1972** |

**状态指纹逐格相同**（9 键；baseline `A+` 与 candidate `A+-checkpoint`）：

| 键 | 值（两臂相同） |
|---|---|
| `L` | 1980 |
| `gdn` | `fc1dc3d8b2b456a6` |
| `ple` | `753dcd4a6575fbfb` |
| `tail` | `48a3c2533574ea0a` |
| `dead` | `da7bffc5f197103a` |
| `pooled` | `7c4deaf23555f2e4` |
| `pooled_full` | `97839ef7dd8b1975` |
| `kv` | `2264ba3feac4b06a` |
| `ple_prev` | `271,10025` |

引擎日志原始行更硬（**含 `mtp=` 与 `stale=`**，且 `A+` 与 `A+-checkpoint` **整行逐字符相同**）：

```
L=1980 gdn=fc1dc3d8b2b456a6 ple=753dcd4a6575fbfb tail=48a3c2533574ea0a
pooled=7c4deaf23555f2e4 kv=2264ba3feac4b06a mtp=5d2055678191c2b0 stale=14650fb0739d0383 dead=da7bffc5f19...
```

**两臂配置差仅一项**（其余全同：slots 4、min_free 2560、`expert_slots` 9761、kv `k8v4`、
context 262144、spec 2、mtp_max 1）：

| | baseline | candidate |
|---|---|---|
| `conversation_cache_mib` | **0** | **4096** |

### 1.4 结论与限定

- **W713 B3 观察到的「两臂 md5 不同且互换」= 探针串位**（W713 B3 自己列的两个可能之一），
  **不是该路径的非确定性**。该路径的 park / restore 在**状态层是无损的**。
- **[限定]** parity 用的是**工具自己的覆盖参数**（`--spec 2 --mtp-max-t 1 --suffix-draft 0 --spec-min-p 0`），
  与生产参数不同。所以它证明的是「**引擎该机制无损（状态逐字节）**」，
  **不等于**「生产参数组合下逐位对比过」。生产侧的凭据是 W713 B3 的收益实测（-88% ~ -90%）+ 本条机制无损。

---

## 2 采纳动作（生产变更）

| 步骤 | 结果 |
|---|---|
| register | P31：value `1024` -> **`4096`**、status `CANDIDATE` -> **`ADOPTED`**；evidence 重写（含 parity 全文与限定） |
| register 现状 | **41 行（含表头）/ 数据行 40**；分布 **ADOPTED 21 / REJECTED 14 / CANDIDATE 5**；md5 `cfac8c1d54749ebbb0eaf4302febaedc` |
| config | `gen_config.py --write` -> `generated/strata-huihui-ud-iq4_xs.json`（1281 B，md5 `2987efa6b1fdd077fb268b04dd553512`），args 里新增 `--conversation-cache-mib 4096` |
| 推 166 | register + config 双推，**两侧 md5 一致**（`cfac8c1d...` / `2987efa6...`） |
| 生效 | `docker restart -t 60 strata166-407`；**19:12:29 服务就绪**（`/v1/models` HTTP 200） |
| 复验 | `verify_config.py` -> **PASS=18 FAIL=0**（退出码 0）；新增项 `P31 --conversation-cache-mib 4096` 在 **config JSON + 引擎启动行**双命中 |
| 显存 | 重启后 `572 MiB of VRAM free` ---- **与会话缓存无关**（该缓存走 host RAM，不占显存） |
| 资源 | 166 RAM 128.7 GB（available 119.6 GB），4 GiB 预算余量充足 |

**受益域**（照 register verdict）：多轮**同会话追问**；单次请求无收益；代价 = 按预算占 host RAM。

---

## 3 C4：工具件自包含（并修掉一个真 bug）

**原状**：`deploy/params/gen_config.py` 与 `verify_config.py` 都写
`sys.path.insert(0, r'D:/workbuddy/_z_rk80')` 再 `import _sshutil` ---- 运行期依赖 **routeK 旧区**。

**处置**：

1. `_sshutil.py`（5464 B，sha256[:16] `082fbba5576cb2cc`）**收进** `deploy/params/`，两侧读回相等；
2. 两处 `sys.path.insert(0, HERE)`（脚本自身目录），**运行期依赖归零**；
3. **发现并修一处真 bug**：`gen_config.py` 的 `live_cfg()` 仍读 **base 版旧文件名**
   `data/strata-ud-iq4_xs.json`（W715 切换时漏改）---- `--live` 会拿**旧的 base config** 去 diff。
   已改指 `data/strata-huihui-ud-iq4_xs.json`；
4. `verify_config.py` 两处 **docstring** 里的旧路径同步改（描述当前行为，留着会误导）；
5. `_batchA.py` / `_batchA2.py`（W708c 时代的一次性扫描脚本）加**「过期、勿再运行」标注**，
   **未改其代码** ---- 它们不是运行期工具件，改了反而像"还能跑"。

**自证**：`py_compile` 三件通过；`py_compile` 后 `gen_config.py --live` **rc=0 且输出「与 166 现行 config 的差异：(无差异)」**
---- 这同时反证第 3 步的修正是对的（用旧文件名会 diff 出一堆差异）。

---

## 4 C5：避坑回写

`W709_HANDOVER.md` §4（避坑清单）新增两条（10764 -> 12136 B）：

6. **要拿「引擎这次启动用的什么参数」，读引擎日志文件，别读 `docker logs`**
   （`engine started:` 只写 `/data/strata-<model>.log`；`verify_config.py` 正是靠日志里**最后一次**该行做锚点）。
7. **`tools/` 下的引擎级工具必须在容器内跑，不能在 166 宿主上跑**
   （`/src` / `python3` 都只在容器内；宿主上 `cd /src` 失败而 `set -u` + `&&` 让它**静默退出**，
   日志只留一个 `EXIT=1` ---- 本轮**真实踩到**，浪费了一轮）。
   正解：起同设备同挂载的临时容器；该窗口**独占 GPU**，先停生产、跑完拉回。

---

## 5 副产品观察（转待办，未下结论）

本次重启的引擎启动块里出现几行新内容（0.1.41 自带，此前未留意）：

| 行 | 含义 | 处置 |
|---|---|---|
| `prefill: the CPU share is ON by default for prompt chunks below 1024 tokens ... STRATA_PREFILL_CPU_SHARE=0 turns it off` | 官方 release note 明说 "**AMD are as before**"，但本机（HIP/gfx906）**打印了这行 banner** | **待核**：banner 是否无条件打印？P23 的判据需重审 |
| `strata hc: CUDA0: the hyper-connection read runs as staged ... checked bit for bit against the plain read on this card` | 0.1.41 的 HC staged read（自校验） | 记录 |
| `strata verify: window up to 6 tokens, 88.3 MiB of device buffers` | verify 窗口读数 | 记录 |

---

## 6 待办更新（`W713_PLAN.md` §6 同步改）

- **§6.2 #2（P31/P33）**：P31 **已关**（本条）；**P33（`pin=N`，请求级）仍未测**。
- **§6.2 #8（C4）/ #9（C5）**：**已关**（本波）。
- 其余不变：P23 CPU_SHARE（**新加"banner 是否在 AMD 生效"的待核项**）· P29 GUMBEL · P28 GR_SPLIT ·
  `--kv-grow` · C3 清理 · 上游 feature request · vision 段无独立核验。

---

## 7 回滚（一条命令）

```bash
# 166 上
cp -f /home/albus/strata166/data/strata-huihui-ud-iq4_xs.json.bak_w717_20261009_190837 \
      /home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
cp -f /home/albus/strata166/params/PARAM_REGISTER.tsv.bak_w717_20261009_190837 \
      /home/albus/strata166/params/PARAM_REGISTER.tsv
docker restart -t 60 strata166-407
```

本机侧：`deploy/params/PARAM_REGISTER.tsv.bak_w717_*`、`generated/strata-huihui-ud-iq4_xs.json.bak_*`、
`gen_config.py.bak_c4_*` / `.bak_c4b_*`、`verify_config.py.bak_c4_*` / `.bak_c4b_*`、`W709_HANDOVER.md.bak_c5_*`。

---

## 8 证据索引

| 件 | 位置 | 指纹 |
|---|---|---|
| 工具 stdout（含 PASS 行） | `deploy/tmp/_w717_parity_tool.log` | 1550 B, md5 `e344ec5f50e3595f` |
| parity 结果（含状态指纹） | `deploy/tmp/_w717_parity_results.json` | 6822 B, md5 `ee0132b5a8d3315e` |
| baseline 引擎日志 | `deploy/tmp/_w717_parity_baseline.log` | 7852 B, md5 `17e262d4436064f5` |
| candidate 引擎日志（含 STATE_HASH 原行） | `deploy/tmp/_w717_parity_candidate.log` | 11486 B, md5 `8bc95049e3f2ed4a` |
| 166 侧 parity 输出目录 | `/home/albus/strata166/data/parity/p31_reuse_20261009_190156/` | 已 `chmod a+rX` 可复核 |
| 复验输出 | 本报告 §2（`PASS=18 FAIL=0`） | `verify_config.py` 现算 |

> 过程脚本（本机）：`_p31recon/pre/src/go/run/poll/done/evi/reg/push/verify/evifetch.py`，
> 均在 `C:\Users\clyde\AppData\Local\Temp\`（本工作区新写 `.py` 有三视图不一致的老毛病，故走 Temp）。
