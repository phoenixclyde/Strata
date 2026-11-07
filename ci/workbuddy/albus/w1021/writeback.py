import io

PLAN = "deploy/W832_OPT_PLAN_V2.md"
PROG = "deploy/PROGRESS.tsv"

BLOCK = '''
### 回写 · W1021（完整 review：做了 / 没做 / 为什么 / 正规做法）

机主令「完整 review，不相信做过的任何一个动作」。本节把本轮所有动作逐条**重新取证**，不合格的当场改。

**一、做了，且已独立复核（每条给的是复核命令看到的东西，不是"我记得做过"）**

| # | 动作 | 复核证据 |
|---|---|---|
| 1 | 主线 rebase 到上游 v0.2.11 | `HEAD=53720031`、tag `mi50-0.2.11-r33-3`、`behind=0 ahead=66 merges=0`、`origin==local`、`dirty=0` |
| 2 | 所有活分支 rebase | `main=4533def2`（behind 0）、`exp/R90-080=53720031`（=主线 tip）；`pre-rebase/*`(7)+`backup/*`(2) 未动（存档） |
| 3 | 树能编 | `rm -f strata` 后全量 **154/154、LINK_OK、md5 5e63174d、`strata --version` = 0.1.57** |
| 4 | 镜像换了树 | `strata-gfx906:0.2.11-101`（sha256 `71afeb5c…`）；`/src/src/prefill/moe_mmq.cu` md5 `2d5abbfb`、`GGML_PREC_Q8` 计数 **0**（移植在）；`BUILD-IMAGE.json` = v0.2.11/66/engine **0.1.57**/llama 3cf0325 |
| 5 | 引擎换了 | `/data/bin/strata-0.1.57-001` md5 `5e63174d`、`--version` = **0.1.57**；config `exe` 指向它；cfg md5 `53ac61e0` |
| 6 | 容器换了 | `4f9d5c5b`（image 0.2.11-101）、`restarts=0`、`/health` ok（60 s） |
| 7 | 性能不是白换 | prefill@2K **531.56**（vs 513.65，**+3.5%**）、@8K **715.98**（vs 684.62，**+4.6%**）、decode 34.75（band 10.96，噪声内）、TTFT 3.94 s（−3.8%） |
| 8 | 技能落地 | `~/.workbuddy/skills/strata-release/SKILL.md`：七步 + API 移植 + 四个指针 + 失败模式表 |

**二、没做（每条写清为什么，以及正规做法该怎么做）**

| # | 没做 | 为什么 | 正规做法 |
|---|---|---|---|
| 1 | **质量门**（KL / top-1） | `quant_quality.py` 要独占 GPU（自起引擎），且本机无 Q8_0 金标（`P330`）；我选择先出速度数 | 换上游=可能改比特，**必须**跑相对门（KL≤0.0139 / top-1≥99%，对现役配置），停机 4–6 分钟 |
| 2 | 16K/128K、多轮、MTP 接受率 | 只跑了 2K/8K 单轮 | 六长度档 + 多轮（`prefill_multiturn`）+ spec 接受率，一起进发布记录 |
| 3 | 完整（apt/pip）Dockerfile | tuna pip 源在 01:32 不可达 | 镜像必须**能从零重建**：pip 走离线 wheel 或双源重试，并钉住 base image digest |
| 4 | 清理 | 11 个 exited 容器（最早 5 天）、`-091` 这个"新引擎旧标签"仍在 `/data/bin` | 保留 N-1（镜像 + 二进制 + config 备份）即可，其余删；错版本加 `.superseded` 后缀 |
| 5 | 单 TU 拼装的废止 | `ci/build.sh` 仍是单 TU 工具，发布却用它验过 | 发布只用全量构建；`build.sh` 明确标注"仅调试" |

**三、为什么出错（根因，不是事后总结）**

1. **合并 ≠ 能编**：上一轮只编了 `prefill.cpp` + `gemm.cu` 就写"merge 可编"；全量一编 4 处 API 断裂。
2. **link 成功 ≠ 干净**：旧 `.o` 复用造出过一版混合二进制（md5 `a93ac842`），差点被当成成品。
3. **版本是四个指针**：tag / `BUILD-IMAGE.json` / binary / **编译期 `-DSTRATA_VERSION`**；我只动前两个，
   于是部署出一个"新引擎、旧标签"的 `-091`——机主一句"引擎还是 0.1.56？"把它问出来。
4. **镜像是隐形的第三份树**：容器只挂 `/data`、`/models`，`/src` 来自镜像；我最初按"挂载"思路排计划。
5. **同一人既做变更又做验收**：本轮每次"验收"都是我自己跑的，没有独立的第二遍。

**四、正规做法（已写进技能，未来按这个执行）**

1. 发布清单固化成脚本，**每条指针都有验证命令**，四点必须一致才允许收工。
2. 变更与验收分离：build → 部署 → 质量门 + 六长度档 → 才切生产；任一步失败自动回滚。
3. 版本单一来源：`-DSTRATA_VERSION` 不再依赖 cmake 缓存（构建时从 `git describe` 注入）。
4. 发布产物只来自**全量构建**；单 TU 构建仅用于调试。
5. 镜像可重现 + 记录 base digest；`BUILD-IMAGE.json` 由构建脚本生成，不手写。
6. 回滚常态化：保留 N-1 镜像 / 二进制 / config 备份，`ci/rollback.sh --exe` 一条命令。
7. 每版都跑同一套 bench（2K/8K/16K + decode + 多轮），结果进 `ci/state/cfg/` 与账本。
'''
s = io.open(PLAN, encoding="utf-8").read()
if "回写 · W1021" not in s:
    s = s.rstrip("\n") + "\n" + BLOCK
s = s.replace("引擎 `strata-0.1.56-091`（md5 `972fb977…`，`-DSTRATA_VERSION` 仍 0.1.56，正在按 0.1.57 重编）",
              "引擎 `strata-0.1.57-001`（md5 `5e63174d…`，`--version` = 0.1.57）；容器 `4f9d5c5b` 跑 `0.2.11-101`")
io.open(PLAN, "w", encoding="utf-8", newline="\n").write(s)

ROWS = [
 ("B8工程", "P348", "完整 review：9 项已复核、5 项未做（质量门/长上下文/可重现镜像/清理/单 TU 废止）、5 条根因", "W1021", "DONE",
  "**W1021 立**：逐条复取证据（HEAD 53720031/behind 0/merges 0/origin 一致；154/154 编过且 `--version`=0.1.57；镜像 sha256 71afeb5c、/src 含移植；引擎 md5 5e63174d 且 config 指向；容器 4f9d5c5b restarts=0；"
  "prefill 2K +3.5%、8K +4.6%）。未做：质量门（需独占 GPU 且无 Q8_0 金标）、16K/多轮/MTP、可重现镜像（pip 源不可达）、旧容器清理、单 TU 构建依然用于发布。根因：合并≠能编、link≠干净、版本四指针、镜像第三份树、自验无第二遍。",
  "deploy/W832_OPT_PLAN_V2.md §6.5 回写·W1021"),
 ("B5本机缺口", "P349", "发布四指针校验：tag / BUILD-IMAGE.json / binary / 编译期 `-DSTRATA_VERSION` 必须一次给齐", "W1021", "OPEN",
  "**W1021 立**：`-091` 事故证明版本有四处独立写法。清单：`git describe`、`docker run --rm <img> cat /src/BUILD-IMAGE.json`、`docker exec <c> /data/bin/<exe> --version` + md5、`grep -c 0.1.57 _ci_all.txt`。"
  "四项不一致即视为发布失败。下一步把这段做成 `ci/release_check.py`（现在还没有脚本，只有本节文字）。",
  "deploy/W832_OPT_PLAN_V2.md §6.5 回写·W1021"),
]
lines = io.open(PROG, encoding="utf-8").read().split("\n")
hi = next(i for i, l in enumerate(lines) if not l.startswith("#") and l.count("\t") >= 9)
head = lines[hi].split("\t")
ID = head.index("id")
have = {l.split("\t")[ID] for l in lines if l.count("\t") >= 9}
add = ["\t".join([b, pid, item, src, "count", "1", "1", st, note, ref])
       for b, pid, item, src, st, note, ref in ROWS if pid not in have]
if add:
    while lines and lines[-1] == "":
        lines.pop()
    lines += add + [""]
io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
print("plan block + %d rows" % len(add))
