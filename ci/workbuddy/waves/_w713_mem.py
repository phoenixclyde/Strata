# 记忆追加：v0.1.41 取证（补丁面归零）+ B1b 首轮结果 + 方案优化
import io

p = r"D:/workbuddy_space/strata_ws/.workbuddy/memory/2026-10-08.md"
note = """
## W713 上游 v0.1.41 取证（2026-10-08 22:0x-22:1x，机主令"又有新 release，你更新吧"+"同步考虑方案是否要继续优化"）
- 上游 v0.1.41（10-08 12:14:59Z = 20:14 CST）。源码 zip 本机直下 **9.37 MB/s**，
  sha256 `e5e9a45ed42536c792157654b4d98309565f2d3797d1819c5cebe61c4d94d611`。
- 全树比对（0.1.40.4 -> 0.1.41）：2,262 -> 2,422 文件；**新增 160**（多为 bench/results 社区目录）、**改 75**、删 0。
- **[里程碑] 补丁面归零**：对 0.1.41 **原始树**跑补丁器 = `patched=0 / verified=6 / failed=0`（第二遍同）。
  独立复核：CMakeLists 第 1270 行 `if(STRATA_Q6K_EXPERTS OR STRATA_HIP_GFX906)`（含我们写的注释）、
  strata_hip.h 第 52 行 `#define cudaEventBlockingSync hipEventBlockingSync` —— 两处都是**我们补丁的原文**，
  即 **PR #1396 已合并**。0.1.40.4 的原始树里这两处都没有（已实测对照）。
  => 补丁器**保留为纯验证器（回归闸门）**，不再改源码。`LLAMA_CPP_COMMIT` 未变 => llama.cpp 包继续复用。
- v0.1.41 里与我们相关的关键条：#1353（专家已在 RAM 时改走少线程 prompt reader；官方称某 reporter 曾因此慢 4-7 倍，
  我们正是"全专家驻 RAM + GGUF in place"场景；开关 `STRATA_STAGER_SSD=0/1` => 新候选 P35）；
  #1454/#1465 省 320 MiB 显存（我们 VRAM 紧）；tokenizer 缓存（89K prompt 0.32 -> 0.07 s）；
  #1347 会话缓存淘汰修复（P31/P33 值得重测）；#1317/#1407 挂死引擎自动重启（`STRATA_ENGINE_STALL_S`，需 psutil）；
  `strata --version` 新增。与我们无关：`--batch-groups auto`（多卡）、CPU 助算默认（**官方明写 AMD 照旧**）、
  GDN_CHUNKED（<128 SM 更慢）、FS_SLOTS、ROUTE_RESIDENT（改答案）、STAGE_PIN（有答案损坏报告，仅测量用）。
- **B1b 首轮结果（0.1.40.4，三臂 x 三档，Z0=off）**：假设成立且有明确赢家 = **`--prefill 4096` + `--prompt-cache-every 4096`**。
  4,600-token 会话：温 TTFT **10.58 -> 3.59 s（-66%，reused 0 -> 4096）**；23.9k：温 17.01 -> 9.24 s（reused 16384 -> 20480），
  但**冷预填 50.02 -> 55.70 s（-11%）**。`2048/2048` 短会话收益相同、冷预填更差（23.9k 冷 68.44 s）=> 取 4096 不取 2048。
  仍有一个**结构性盲区**：< 4,096 的极短会话依旧零复用，再降 chunk 只会更慢。
  **收口还差三件**：① 答案是否变（chunk 改 prompt 路径累加顺序 => 必须做低比特差异检查）；
  ② 在 0.1.41 上复核；③ 冷预填代价入结论。三项齐了才谈采纳（动基线 P10 + P34 值）。
- **方案优化**：新写 `deploy/W713_PLAN.md` 取代 `W712_PLAN.md`（后者标注"已被取代"）。三处实质优化：
  ① 第一优先 = 升级 0.1.41（补丁面 0）；② 把"升级闸门"标准化成脚本（服务面四项 + 中性矩阵，约 10 分钟，
  可跨版本对齐 —— 因为上游一周约 20 个 release，不能再靠一次性人工编排）；③ 新增 P35(`STRATA_STAGER_SSD`)
  并让 P31/P33 因 #1347 复活。
- 取证产物：`deploy/transfer/strata-src-0.1.41.zip`、`deploy/tmp/_w713_relnote.txt`（release 全文 14,385 字符）、
  `_w713_tree_diff.txt`、`_w713_dry411_run1.txt`、`deploy/tmp/src411/`（原始树）、脚本 `waves/_w713_*.py`。
- **待办顺序**：W1 升级 -> W2 闸门 -> B1b 收口(答案差异 + 0.1.41 复核) -> B7(P35) -> B3 -> B2 -> B6 -> B4 -> B5 -> C4/C5 -> C1 -> C3。
"""

with io.open(p, "a", encoding="utf-8", newline="\n") as f:
    f.write(note)
print("appended", len(note))
