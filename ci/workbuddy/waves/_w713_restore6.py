# 重建 W713_PLAN §6 全量账（原节被我的"截断续写"误删）+ 日志
import collections, hashlib, io, os

WS = r"D:/workbuddy_space/strata_ws"
PLAN = os.path.join(WS, "deploy", "W713_PLAN.md")
BAN = [0x21D2, 0x2192, 0x2014, 0x2013, 0x2026, 0x2265, 0x2264, 0x2260, 0x2212, 0x00D7]

SEC6 = """
---

## 6 全量账：已做 / 没做 / 重做（截至 2026-10-08 23:0x CST）

> [!] 本节曾因作者一次"截断到标题再续写"的误操作被整节删除（同步替换 §5 时），
> 已按当前真实状态**重建**；重建依据 = 本会话的各次落盘脚本与 `W713_AUDIT.md` / `W713_UPGRADE.md`。

### 6.1 已做（13 项，带证据）

| # | 事项 | 证据 / 指纹 |
|---|---|---|
| 1 | 工作区迁移 + **原件删除** | 逐文件 md5 全等；删前 "源 ⊆ 目标" + 2 个白名单快照；`MAP_OLD_TO_NEW.md` §5/§6 |
| 2 | 引擎 **0.1.40.2 -> 0.1.40.4** 升级 + 切换 + 复验 + 中性 A/B | 冷预填 -0.33%、温 TTFT -1.7%、`reused` 同；`W712_UPGRADE.md` |
| 3 | **引擎 0.1.40.4 -> 0.1.41 升级 + 切换** | 补丁面**归零**（`PATCH_SURFACE_ZERO`）；镜像 `c45268e786e1`；容器 `-405` 35 s 就绪；`W713_UPGRADE.md` |
| 4 | 升级闸门脚本化 + **首跑** | `deploy/scripts/upgrade_gate.sh`；服务面 7 项全过 + 中性矩阵（三档 `reused` 逐格相同、差 <=1.4%） |
| 5 | 参数最优波（W709）三项 ADOPTED | `--pcie-frac 0.20` / `--spec-min-p 0.70` / `--prompt-cache-every 8192` |
| 6 | 机制三条实证 | chunk 边界规律 / `--prompt-cache-tail` 重复 / 8192-16384 盲区（证据等级已在审计后分级） |
| 7 | **A2 解码基准**（0.1.40.4） | 引擎行 45.7 / 43.3 tok/s；探针中位 43.53 |
| 8 | **B1 边界矩阵**（9 格全中，0.1.40.4） | `<8k` 三臂全 0；`8-16k` 只有 8192 有效（5.87 vs 23.07 s）；`>16k` 8192=16384、32768 归零 |
| 9 | **B1b 收口**（0.1.40.4 首轮 + 0.1.41 复核 + **答案测试**） | 收益 -70.6% 温 TTFT / 代价 冷预填 -11~-23% / **答案会变** => **不改基线 P10**（结论已入 register P10 evidence） |
| 10 | **固化审计 + P34 / P10 结论入 register** | register `f82ccdd743ff...`（本机==166）/ **35 行 / 16-12-7**；`gen_config --write` 后生产 config **逐字节未变** |
| 11 | **三路独立对抗性审计**（+ 6 条 P1 全处置） | `W713_AUDIT.md`（含无法验证清单 6 条与三条元结论） |
| 12 | **CPU 侧实测**（Intel / 无 AVX-512 / AVX2 + 22 线程） | 本件 §1 ⑤；修正了 #795 与 P23 的判读 |
| 13 | 通用切换脚本 | `deploy/scripts/switch_strata.sh`（旧容器自动探测 + 自动回滚），取代"一次升级一个专用脚本" |

### 6.2 没做（11 项，按优先级）

| # | 事项 | 说明 |
|---|---|---|
| 1 | **B7 / 新候选 P35 `STRATA_STAGER_SSD`** | 0.1.41 #1353 的目标场景正是我们；用于判定我们走的是哪条 prompt reader 路径 |
| 2 | **B3 P31/P33**（`--conversation-cache-mib` / `pin=N`） | 0.1.41 修了满缓存淘汰逻辑（#1347）=> 值得在这版重测 |
| 3 | **B2 P23 `STRATA_PREFILL_CPU_SHARE`**（+ `_MAX=3072` 次级臂） | CPU 有 22 线程富余；官方 AMD 保持 opt-in（需自测）；**答案非逐位一致须同报** |
| 4 | **B6 P30 `STRATA_MMVQ_IL` 命中判定** | 读源码即判，无需发车 |
| 5 | **B4 P29 `STRATA_SPEC_GUMBEL`** | 必须采样口径（temperature>0），>=5 轮/臂 |
| 6 | **B5 P28 `STRATA_GR_SPLIT`**（同族低优先 `--kv-grow`(P32)） | 预期 ~3% < 分辨力 => 只用机制判据 |
| 7 | 0.1.41 的 **#1454 省 320 MiB 显存** 与 **tokenizer 缓存** 两条未单测 | 本波闸门只覆盖预填/温 TTFT/reused |
| 8 | **C4** `gen_config.py` / `verify_config.py` 的 `_sshutil` 自包含缺口 | 工具件，不走参数通道 |
| 9 | **C5** `docker logs` 拿不到终态启动行 -> 回写 `W709_HANDOVER.md` §4 | 运行期避坑 |
| 10 | **C3 旧镜像/容器清理** | 现 5 镜像 / 5 容器（-401/-402/-404/-405 + `strata166`），需定保留策略；走 `docker-disk-truth` 技能 |
| 11 | **向上游提 feature request**（B1b 派生的最干净路径） | 让可复用 checkpoint 落在**子 chunk 边界**而不改 prefill chunk => 既不换数值路径、又补上短会话盲区 |

### 6.3 重做（4 项）

| # | 事项 | 理由 |
|---|---|---|
| 1 | **0.1.41 的解码基准（A2 的 0.1.41 分母）** | 闸门只覆盖预填 / 温 TTFT / `reused`；**解码口径仍缺新分母**，而多数 B 档要拿解码数字比 |
| 2 | 0.1.40.x 的其它读数若要引用需在 0.1.41 重取 | 闸门只复核了三档（100/220/530），其余档位未重测 |
| 3 | 0.1.40.1 时代的历史读数（预填 438.8 / 解码 42.9 tok/s） | **仅存档**，不得当现行基线 |
| 4 | 审计的残余未验证项（PR #1396 徽章/提交哈希、166 侧下载来源、C-530 中位数等） | 见 `W713_AUDIT.md` §4；能补的补，补不了的要一直标注 |

> **不重做、也不得引用的**：`waves/_w727.out.txt`（测试域无效：6,833-token prompt 短于一个 chunk）。
"""

t = io.open(PLAN, encoding="utf-8").read()
assert "## 6 全量账" not in t, "§6 已存在，勿重复追加"
assert "### 6.3" not in t
io.open(PLAN, "w", encoding="utf-8", newline="\n").write(t.rstrip("\n") + "\n" + SEC6)
d = open(PLAN, "rb").read()
print("W713_PLAN.md 重建后：bytes=%d CR=%d BAN=%d" % (len(d), d.count(b"\r"),
      sum(1 for c in d.decode("utf-8") if ord(c) in BAN)))
# 结构自检
for k in ["## 5 附", "## 6 全量账", "### 6.1", "### 6.2", "### 6.3", "B1b 收口**（0.1.40.4 首轮 + 0.1.41 复核", "向上游提 feature request"]:
    print("  结构自检 %-46s %s" % (k, "OK" if k in d.decode("utf-8") else "MISS"))

# 日志补记
log = os.path.join(WS, ".workbuddy", "memory", "2026-10-08.md")
io.open(log, "a", encoding="utf-8", newline="\n").write("""
## W713f B1b 收口落盘 + 一次自伤（2026-10-08 23:0x）
- register 的 **P10 evidence** 追加了 B1b 收口结论（值/状态不动）：md5 `3dc808ceaf03` -> `f82ccdd743ff`，仍 **35 行 / 16-12-7**，CR/BAN 0；
  `gen_config --write` 后生产 config **逐字节未变**（`d2b10f0c...bea`）。
- **自伤**：用"截断到 §5 标题再续写"的方式替换 §5，把紧随其后的 **§6 全量账整节删掉**（19,045 -> 14,317 字节）；
  是脚本里下一句"§6.2 锚点必须命中 1 次"的断言把它暴露出来的（否则会静默丢一整节）。
  当时**没有 W713_PLAN.md 的备份**（只有 register 的备份），已按当前真实状态**重建 §6**（13 已做 / 11 没做 / 4 重做），
  并在节首注明"曾被我误删、已重建"。教训：**改既有长件前先备份该件本身**（本次只备份了 register，没备份被改的文档）。
- §6 重建时顺手把账本推到当前真实：W1 切换 / W2 闸门脚本 / **B1b 收口** / 三路审计 全部移入"已做"；
  新增"向上游提 feature request（子 chunk 边界 checkpoint）"作为 B1b 的替代路径。
""")
print("日志已补记")
