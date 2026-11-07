# W716 对抗性审计报告（覆盖 W714 / W715 / W716 三波）

- 日期：2026-10-09 02:3x（本机时间）
- 方式：**独立子 agent**（Explore 类型，工具集无写权限 = 只读结构保证）；只读本机 + 经 ssh 只读 166
  （`docker exec` 仅 `sed/grep/ls/sha256sum/diff`）
- 四条铁律：**独立上下文 / 只读 / 对抗立场 / 只认原始证据**
- 独立复跑/复算项：`verify_config.py`（得 PASS=17 FAIL=0）、两 pack 全 5 文件 sha256、
  base vs huihui 分片 head/mid/tail 抽样、容器内 `sed` 取源码原文、`ldd` 判构建形态
- **计数：`P0=0 P1=2 P2=7 UNVERIFIABLE=2`**（另「无法验证清单」5 条）
- 总判：**三波的核心结论全部未被推翻（0 条 P0）**；问题集中在引证精度、口径混用、账本过期值、指针不全

## 1 审计发现（照录，未弱化）

| # | 严重度 | 类型 | 位置 | 依据 | 后果 |
|---|---|---|---|---|---|
| 1 | P2 | CONFIRMED-FALSE | `deploy/W716_BASELINE.md:16-17`；`deploy/params/PARAM_REGISTER.tsv`(P30) | 容器内 `sed -n '2638,2655p' /src/src/kernels/cuda/native_mmvq.cu`：2641=`#else // HIP: no interleaved path`；2643=`void native_q8_1_interleave(...) {`；**2644=`throw ... "is CUDA only");`**；**2646=`bool native_mmvq_il_supported(int,int,int) { return false; }`**；2653=`#endif` | 结论仍成立；但"读源码即判"的行号逐字取不到，可复核性打折。`verify.cpp:107/952/1604` 经核对**正确** |
| 2 | P2 | CONFIRMED-FALSE | `deploy/W715_HUIHUI_SWITCH.md:42` | 166 上 `diff` 两 pack 的 `compat-bf16.json` 仅 `2c2`，唯一改动是 `"source"` 字段的路径 | 对"差异只在 experts"无影响；但差异**性质**写错了 |
| 3 | P2 | WEAK | `deploy/W716_BASELINE.md:42-47` | huihui 列取客户端 summary（40.51/43.98/46.44），orig 列取引擎日志（36.2/46.9/46.7）---- 两臂**取自不同来源** | 差 <=0.25% 且偏心方向偏向 huihui；"同口径同批次"措辞不成立，"无退化"结论不变 |
| 4 | P1 | UNVERIFIABLE | `deploy/W716_BASELINE.md:86` | 全库 grep `22.88` 只命中报告本身；166 日志里的 `really free` 值是 25.10/13.49 与 12.37/23.77 | 该行被指"无原始支撑"（**本裁决推翻，见 §2 #4**） |
| 5 | P2 | WEAK | `deploy/W716_BASELINE.md:56-57` | W716 只重测 3 档预填/解码 + 2 档前缀；P25/P06/P34 的**最优值未在 huihui 上重测** | 把"未重测"表述为"仍成立" |
| 6 | P1 | UNVERIFIABLE | `waves/_w714o_oids.py`（输出未落盘） | 已留档的只有**字节同一性**；"= huihui-ai 仓"的独立锚（hf-mirror LFS oid）**输出未保存** | "D盘=abliterated"成立，但"= huihui 仓"当时无法从记录复核（**已补做，见 §2 #6**） |
| 7 | P2 | CONFIRMED-FALSE | `deploy/W716_BASELINE.md:115` | §6 所指的两个"两臂原始输出"文件**只含 §2 的 3 档探针**；§3 前缀探针与 §4.1 槽位读数不在其中 | 结论可查（审计已从 166 日志复证），但报告给的证据指针不全 |
| 8 | P2 | CONFIRMED-FALSE | `deploy/params/PARAM_REGISTER.tsv`(P09/P08/P07) | 账本仍写 `9758 槽`；现役 huihui 运行态实测 **9757 槽** | 同一对象账本取值 != 当前运行态；参数值(`auto`)不受影响，但"账实一致"被破坏 |
| 9 | P2 | WEAK | `deploy/W716_BASELINE.md:68` | 报告写"400 段（18,085 tok）"；引擎原文 `prompt 18096 tokens = ...` | 数值小差；`reused=16384` 结论不受影响 |

## 2 逐条裁决（成立就改 / 不成立写明为何）

| # | 裁决 | 处置 |
|---|---|---|
| 1 | **成立** | 已改 `W716_BASELINE.md` §1 代码块（throw 记 2644、恒 false 记 2646）；已改 register P30 evidence 同样两处行号 |
| 2 | **成立** | 已改 `W715_HUIHUI_SWITCH.md` §1.2：差异性质改为「唯一实质差异是 `"source"` 字段的路径（`/weights/...` 变 `/models/huihui-ai/...`），166 上 `diff` 实测仅 `2c2`」 |
| 3 | **成立**（作者自查亦发现） | 已把 §2 表的"解码 t/s"**六格全部改为引擎日志行口径**（huihui 43.9/48.2 等），并在表下加口径声明 |
| 4 | **不成立** | 该值有原始出处：两臂启动行 `expert cache auto: 22.88 GiB free, 700 MiB reserved (+218 MiB for the draft head) -> 6779 / 6780 slots`（两臂逐字相同）。审计 grep 的是**另一行**（`FileExpertSource: ... really free for a ... page-locked complement`，值 25.10/13.49 与 12.37/23.77），那是**分配 page-locked 时的瞬时可用量**，与 expert cache 分配不是同一指标。**根因在我：没写出处。** 已在该行加"（取启动行 `expert cache auto` 的 free 值）"，并补一段"勿与 `really free` 混"的说明 |
| 5 | **成立** | 已改 §2 判定：加"本轮只重测 3 档预填/解码 + 2 档前缀；P25/P06/P34 三条的**最优值并未在 huihui 上重测** ---- 本节只支撑'基线量级未变'，不等于'参数结论已复核'；三条参数的正确表述是**沿用 base 结论、待重测**" |
| 6 | **成立** | **已补做**：重跑 hf-mirror 两仓 `tree/main?recursive=true`，把 `UD-IQ4_XS/` 三片与 mmproj 的 **LFS oid（= 文件内容 sha256）** 落盘 `deploy/tmp/_w714_hfm_oids.txt`（2065 B）。三个锚逐条验在位：`c67b468b...c161` / `130560b6...8e2c`（huihui 仓）、`577a38a2...aaa7`（unsloth 仓） |
| 7 | **成立** | 已补 §6：给出 §3 的 166 日志行号（218/229/244/254）与 §4.1 的槽位读数行出处 |
| 8 | **成立（部分）** | `9758` 本身是 **base 态实测值**，保留不改；已在 P07/P08/P09 三行加注「（base 态）」并补 huihui 态 `9757`。register 已推 166，两侧 md5 `ee91c9553d9054a967b771da9217562d` |
| 9 | **成立（口径差）** | 已注明「客户端计 18,085 / 引擎计 18,096」（150 段 6,838 / 6,849 同理） |

## 3 「无法验证清单」（审计给出）与裁决

| # | 审计的无法验证项 | 裁决 |
|---|---|---|
| 1 | §4.1 的 `free VRAM 22.88 / 22.88` | **不成立**（见 §2 #4，出处为启动行；已补出处与防混说明） |
| 2 | 「D盘/现役 huihui = huihui-ai 仓」的仓属锚 | **成立**（当时未留档）=> **已补做**（见 §2 #6） |
| 3 | §3 / §4.1 的原始数据不在报告所指文件中 | **成立** => 已补指针（见 §2 #7） |
| 4 | W715 §3.3「约 200 是图像 token」 | **成立** => 已改为「总 prompt = 262 tokens（图像 token 数未单独测，只证到总数）」 |
| 5 | §2「两臂先后启动、同批次」 | **成立** => 已改为「同一探针、同一参数、同一台机器，**串行各跑一次**（02:05 / 02:11，相隔约 6 分钟；显存放不下两个引擎，无法并行）」 |

## 4 审计独立复证为「成立」的断言（供对照）

A1 base 三片钉死值 ✓ · A2 D盘全量 = huihui 实体 ✓ · **A3 抽样对撞失效（审计在 166 现场重取，两组逐格完全相同）** ✓ ·
A5 weights 目录软链 + 删前全量 sha256 相等 + 释放约 918 MB ✓ ·
**B1 两 pack 五文件：四件相同 / compat-bf16 差 4 行（性质见 §1 #2）** ✓ · B2 两侧 md5 ✓ ·
**B3 独立跑 verify_config.py = PASS=17 FAIL=0** ✓ · B4 strata-vision 7,754,632 B（审计另给 sha256 `fadfa15a...`）✓ ·
B5 vision 三键 = register V00-V02、mmproj `b1a82259...` ✓ · B6 PLE 行 ✓ · B7 容器态 ✓ · C1 结论（ldd 证实 HIP）✓ ·
C2 MTP 249/290 与 249/280、reused 三档 ✓ · C3 前缀行 ✓ · C4 槽位 9757/9758 + 借槽 + 余量 ✓ · C5 MEMORY.md md5/字符数/归档 ✓

## 5 本波教训（可复用）

1. **引证行号必须现场 `sed` 取原文后再写** ---- 本波 3 处行号各有 1~2 行偏移，根因是凭 grep 输出转写而未逐行核对。
2. **同一张对照表的同一列必须同源** ---- 本次"解码 t/s"两臂分别取自客户端 summary 与引擎日志。
3. **「无原始支撑」这一指控本身也要核实出处** ---- 审计对 22.88 的判定就是 grep 到了另一行；
   但**根因是我没写出处**：以后凡引用日志值，一律在该值旁写明取自哪一行。
4. **结论的适用边界要显式** ---- 「基线量级未变」不等于「参数最优值已复核」。
5. **审计发现分两类处置**：证据缺口要**补做**（如 #6 的锚），表述缺口要**改写**（如 #1/#2/#5）；不成立的要用原始证据反驳并写进报告（如 #4）。
