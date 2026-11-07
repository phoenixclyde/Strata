import io
import re

P = "deploy/PROGRESS.tsv"
PLAN = "deploy/W832_OPT_PLAN_V2.md"
MEM = ".workbuddy/memory/2026-11-07.md"
HAND = "albus/w1034/HANDOFF.md"

rows = [
 ["B5本机缺口","P527","B3 干净 bench：T≤6 加速、T≥7 悬崖；hc4b 加 MAX_T=6 安全门后大 T 回退持平","W1047","count","1","1","DONE",
  "**实测**：停机窗口 `fused_gr_bench` off/on 各 2 轮，Q8 fast=2。T1–6 整读 −2.3%…−13.2%、down −7.3%…−24.1%；无门控版本 T7/T8 down +45.1%/+64.5%。重建 `gfx906/hc-dp4a@03509d1b` / `strata-0.1.57-hc4b`（md5 `0533074826258d5f96c4b65bc0ad33df` / 43,679,864 B）：`STRATA_HC_DOWN_DP4A_MAX_T=6` 时 T7/T8 与 off 持平（read +0.29%/+0.19%、down +0.42%/+0.14%）。n=3 复测 T4：down 39.87→30.17 µs（−24.33%，CV 0.24%/0.16%）。早先 cold timeout 是 `iters=1` 让中位数空向量越界，已更正为 bench 调用缺陷。","P524;P528","KW:MAX_T|T4|24.33%"],
 ["B5本机缺口","P528","B3 真实模型数值/任务门：fp32 logits KL max 0.00221、needle 两臂 18/18","W1047","count","1","1","DONE",
  "**实测**：同一 `hc4b` off/on，4 个 1K/8K/20K/32K prompt 的全词表 fp32 logits：`pcompare` top-1 **100.00%**、KL mean **0.00087** / median 0.00101 / max **0.00221**。任务级 needle 16K/32K/64K × 深度 0/50/100%，off 9/9、on 9/9，全部 `cached=0`。两次窗口误失败均为 harness（健康字符串匹配、临时服务忘 `-p 8090:8090`），模型无异常。","P527","KW:pcompare|0.00221|9/9"],
 ["B8工程","P529","CI/CD 回溯：本地工具/补丁进 `ci/workbuddy`，全工作区 SHA-256 清单 + 制品账","W1047","count","1","1","DONE",
  "**实测**：`ci/w1047-coverage @ 9e780f581` 含 4446 文件、744k 行：`ci/workbuddy/**` 镜像项目自产脚本/补丁/报告，`ci/provenance/workspace_manifest.tsv` 覆盖 23197 个可审计文件，`selected_scripts.tsv` 对镜像文件逐一 SHA-256，`artifact_ledger.tsv` 对 58 个 `/data/bin` 制品标注 recipe/CI/manual/UNTRACKED。历史 fork/source 快照不整仓塞进引擎仓库，但哈希可审计。","P517;P522","KW:workspace_manifest|artifact_ledger|4446"],
 ["B8工程","P530","CI 触发全覆盖回溯：workflow 扩到所有 push 分支与工具路径，7 个生产/候选 sha 全部有绿 run","W1047","count","1","1","DONE",
  "**实测**：`downstream-gate.yml` push branches 从 3 个白名单改为 `**`，paths 增加 `tools/**` `deploy/params/**` `albus/**` `waves/**`；PR 目标扩到 `gfx906/**`/`ci/**`。`workflow_dispatch` 回溯触发 7 refs 全 success：`af797b90`、`deb41e12`、`e0ce7c96`、`179bd6b5→03509d1b`、`eb5bfbb8`、`b2c82ff0`、`9e780f58`。GitHub 文档核实 branches+paths 为 AND 过滤，故工具路径与全分支同时放开才全覆盖。","P529","KW:workflow_dispatch|7 refs|branches"],
 ["B8工程","P531","历史脚本语法清零：修复 12 个真实语法错误/CRLF，1741 py + 1214 sh 全过","W1047","count","1","1","DONE",
  "**实测**：`workbuddy_syntax.py` 先抓 5 个不可执行文件（引号未转义、三引号嵌套、bash 片段/PowerShell 语法），远端 Linux 又抓 7 个 CRLF shell。全部修复而非豁免：`w920/w932 reg.py`、`_patch_and_rebuild.py`、`fix_watch.sh`、`s02_patches.sh`、`w828/r10*.sh`、`w941/pmc_prefill3.sh`。最终 **1741 Python + 1214 shell PASS**；`workbuddy_selftest.py` 14/14。","P529","KW:1741|1214|CRLF"],
 ["B8工程","P532","GitHub Push Protection 拦下 OAuth 密钥；脱敏后从干净基线重建提交，不 bypass","W1047","count","1","1","DONE",
  "**实测**：首次 push 被 repository rule 拒绝，定位 `deploy/W775_AUDIT_auditor2.md` 含 OAuth 形状密钥。按 GitHub 文档要求从所有提交移除：本地与 bundle 一并替换为 `[REDACTED_GITHUB_TOKEN]`，更新 manifest 哈希、删 `__pycache__`、`git reset --hard` 干净基线后重提 `9e780f581`，pre-push ROUND_GATE PASS。**没有使用 bypass URL**。","P529","KW:Push Protection|REDACTED_GITHUB_TOKEN|9e780f581"],
 ["B10环境与版本","P533","装机 hc4b：B3 DP4A HC down + T≤6 安全门，config 增量仅 exe + 两个 env","W1047","count","1","0","OPEN",
  "**D1–D5 已 PASS，等 D6 后执行**：候选 `strata-0.1.57-hc4b`，config 38 args 不变、env 10→12（`STRATA_HC_DOWN_DP4A=1`、`STRATA_HC_DOWN_DP4A_MAX_T=6`）。D3 T4 −24.33%（n=3）、D4 KL 0.00221/top1 100%、D5 仅声明增量。装机后必须冷启动验 env、health、disk=build=running。","P527;P528","KW:hc4b|D1–D5|冷启动"],
 ["B10环境与版本","R111","GPU CI runner：目前 GitHub 只有静态门，编译/数值/装机仍在 166 手工窗口","W1047","count","1","0","OPEN",
  "**W1047 立**：API 核实 `actions/runners` total_count=0。要让 CI/CD 真正覆盖 build/bench/deploy，需要在 166 注册 self-hosted runner，并把 `ci/build.sh`、A/B、binary_integrity/recipe 作为受控 job；涉及长期常驻服务与凭据，须单独定安全边界，不在本轮擅自安装。","P530","KW:self-hosted|total_count=0|GPU CI"],
 ["B5本机缺口","R112","R110 的真实模型 P/V dump：合成 PV-dot8 上限 1.483× 但 rel-rms 6.23%，未测模型分布","W1047","count","1","0","OPEN",
  "**W1047 立**：R110 原型只证明 i4x8×i4x8 可跑，量化误差和上限不可直接外推生产。需要从一次真实 verify/HC 请求 dump P、Q4_0 V 与 scale，离线做 P(int4)×V(int4) 误差预算，再决定是否接 OPT。","R110;P525","KW:P/V dump|1.483|6.23%"],
]

lines=io.open(P,encoding="utf-8").read().splitlines()
have={l.split("\t")[1] for l in lines if l.count("\t")>=9 and not l.startswith("#")}
for r in rows:
    assert len(r)==11 and all("\t" not in x for x in r), r[1]
    assert r[1] not in have, r[1]
    whole=" ".join(r)
    for kw in r[10].replace("KW:","").split("|"):
        assert kw in whole,(r[1],kw)
lines += ["\t".join(r) for r in rows]
io.open(P,"w",encoding="utf-8",newline="\n").write("\n".join(lines)+"\n")

tot=done=0
for l in lines:
    f=l.split("\t")
    if len(f)>=10 and f[0]!="block" and not l.startswith("#"):
        try: tot+=int(f[5]); done+=int(f[6])
        except ValueError: pass
pct=100.0*done/tot
print("TOTALS",tot,done,round(pct,1))

s=io.open(PLAN,encoding="utf-8").read()
s=re.sub(r"\| 进度分母 \| \*\*\d+ 条 / 已结 \d+ / [\d.]+%\*\*（W1046；",
         "| 进度分母 | **%d 条 / 已结 %d / %.1f%%**（W1047；"%(tot,done,pct),s,count=1)
old="| **唯一队列** | **R109（W1046 置顶，R103 后续移植面：B3 `hc4` 已建未装，先过 off floor + 数值/任务 + 停机 A/B；随后 A1；A5 先解死派发）** → **R110（W1046 新立，k8v4 PV-dot8 独立原型：P(int4)×V(int4)，与 dot8q/R91 均不同）** →"
new="| **唯一队列** | **P533（W1047：B3 `hc4b` D1–D5 已过，待 D6 后装机）** → **R110/R112（k8v4 PV-dot8 真实 P/V dump，合成上限 1.483× 不外推）** → **R111（GPU self-hosted CI runner）** → **R109 的 A1/A5（B3 有结论后再开）** → ~~R103 已装机~~ →"
assert old in s
s=s.replace(old,new,1)
title="### 回写 · W1047（2026-11-07 19:1x–22:3x）CI/CD 全覆盖回溯 + B3 干净门与真实模型门"
block=title+"""

- **上轮纠错**：W1045 说 `pr/k10` 无 pre-push，只对 linked worktree 的错误路径成立；钩子实际在共享 `git-common-dir/hooks`，W1046 已修 installer，W1047 修 `round_gate --status` 的 `git rev-parse --git-path hooks`。CI 零触发的旧结论也被 18:51 后的 runs 更新。
- **CI/CD 回溯完成**：`ci/w1047-coverage@9e780f581` 把本地工具/补丁镜像进 `ci/workbuddy`，23197 文件 SHA-256 清单 + 58 制品账；workflow 全 push 分支 + 工具路径；7 个生产/候选 sha 全绿。Push Protection 拦到真实 OAuth 形状密钥，已脱敏重建提交，未 bypass。
- **B3 从不可判到可装**：clean bench 发现 T7/8 悬崖，`hc4b@03509d1b` 加 `MAX_T=6` 后大 T 持平；n=3 T4 down **−24.33%**。真实模型 fp32 logits top1 100% / KL max **0.00221**，needle 两臂 18/18。D1–D5 PASS。
- **仍未做**：R111 GPU self-hosted CI runner（runners=0）；R112 真实 P/V dump；R91/R110 的 dot8 接入仍不凭合成上限推进。
"""
assert title not in s
s=s.rstrip("\n")+"\n\n"+block+"\n"
anchor="| `回写 · W1045（2026-11-07 18:1x–18:5x）五问审计：移植面 / dot4 / dot8 / mmq / CI-CD` |"
pos=s.index(anchor); eol=s.index("\n",pos)+1
row="| `回写 · W1047（2026-11-07 19:1x–22:3x）CI/CD 全覆盖回溯 + B3 干净门与真实模型门` | hook/worktree 纠错；脚本全量入 CI；B3 hc4b D1–D5 | W1047 |\n"
s=s[:eol]+row+s[eol:]
io.open(PLAN,"w",encoding="utf-8",newline="\n").write(s)

h=io.open(HAND,encoding="utf-8").read()
h=re.sub(r"> SNAPSHOT: round=W\d+ date=2026-11-07","> SNAPSHOT: round=W1047 date=2026-11-07",h,count=1)
io.open(HAND,"w",encoding="utf-8",newline="\n").write(h)

m=io.open(MEM,encoding="utf-8").read().rstrip("\n")
add="""

### W1047（19:1x–22:3x）CI/CD 全覆盖回溯 + B3 可装门

- **纠错**：pre-push 不是从未安装，而是 `pr/k10` linked worktree 使 `.git/hooks` 路径误判；共享 hooks 在 `strata-fork/.git/hooks`。W1047 修 `round_gate --status` 用 `git rev-parse --git-path hooks`。
- **CI/CD**：`ci/w1047-coverage@9e780f581`，4446 文件；workflow 全分支+工具路径；7 sha dispatch 全绿；23197 文件 SHA-256 manifest；58 制品账；12 个历史脚本语法修复；Push Protection 密钥脱敏后重提，未 bypass。
- **B3**：`hc4b@03509d1b` / `05330748…`，`MAX_T=6` 解决 T7/8 悬崖；T4 down −24.33%（n=3）；真实 logits top1 100% / KL max 0.00221；needle 18/18。D1–D5 PASS，P533 待 D6 装机。
- **新开**：R111 GPU self-hosted runner（当前 runners=0）；R112 真实 P/V dump（R110 合成 1.483× 不外推）。
"""
io.open(MEM,"w",encoding="utf-8",newline="\n").write(m+add+"\n")
print("plan/memory/snapshot written")
