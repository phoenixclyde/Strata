# -*- coding: utf-8 -*-
import io
PLAN="deploy/W832_OPT_PLAN_V2.md"; PROG="deploy/PROGRESS.tsv"

# --- PROGRESS: close R99 (count 4 -> done 4, DONE_NEG) and add two rows
lines=io.open(PROG,encoding="utf-8").read().split("\n")
hi=next(i for i,l in enumerate(lines) if not l.startswith("#") and l.count("\t")>=9)
head=lines[hi].split("\t"); ID=head.index("id"); ST=head.index("status"); DO=head.index("done"); CN=head.index("count")
closed=False
for i,l in enumerate(lines):
    if l.count("\t")<9: continue
    c=l.split("\t")
    if c[ID]=="R99":
        c[ST]="DONE_NEG"; c[DO]=c[CN]
        c[8]=(c[8]+" | **W1030 关闭**：S1（`strata-0.1.57-003`，`exp/lcpp-b12169`=`7fdd5d3c`）今天重测——"
              "① **数值不同**：968-token 英文 48-token 贪心输出在**第 59 字符**就分叉（旧「User provided repeated sentence」vs 新「User provided many repetitions of pangram」），"
              "短例 118/122、中文 7/5 亦不同 ⇒ 门1 不过；② `cfg_apply` 2K 直接 **503**，不承受基准的重复请求 ⇒ 无合格速度数。"
              "按方案「门1 不过 = spec 错，禁止进 S2」，两轮修不好即关闭。")
        lines[i]="\t".join(c); closed=True
rows=[("B8工程","P374","R99 关闭：tile_spec 版数值不同（968-token 例第 59 字符分叉）+ 2K 503 ⇒ 不进 S2",
       "W1030","DONE_NEG",
       "**W1030 立**：重测 `strata-0.1.57-003`（S1，b12129+#31047 自建 tile_spec）：门1 贪心指纹三例全不同（en2k 224/224 但在第 59 字符分叉；short 118/122；zh2k 7/5）⇒ 分派数据形状错，不是数值噪声。"
       "门2 `cfg_apply --lengths 2000,8000` 在 **2K 即 HTTP 503**（引擎在重复请求下不可用），故无合格速度数。按 R99 方案「门1 不过禁止进 S2、两轮修不好即关闭」⇒ **DONE_NEG**。",
       "deploy/W832_OPT_PLAN_V2.md §6.6"),
      ("B8工程","P375","更正 W1027 的「S1 在 75-token 上 hang」：今天 67/154/555 token 全部正常返回，hang 不复现",
       "W1030","DONE",
       "**W1030 立**：同一个 `strata-0.1.57-003` 今天探针 67 tok 1.51 s / 154 tok 1.79 s / 555 tok 2.50 s 全 OK，health ok、restarts=0 ⇒ W1027 记的 hang **不可复现**（当时是刚启动后的首个请求）。"
       "真正的缺陷是**数值错**，比 hang 更严重也更难发现：`P363` 的结论据此更正为「不可复现，真实故障是算错」。",
       "albus/w1030/probe_s1.sh")]
have={l.split("\t")[ID] for l in lines if l.count("\t")>=9}
add=["\t".join([b,pid,item,src,"count","1","1",st,note,ref]) for b,pid,item,src,st,note,ref in rows if pid not in have]
if add:
    while lines and lines[-1]=="": lines.pop()
    lines += add + [""]
io.open(PROG,"w",encoding="utf-8",newline="\n").write("\n".join(lines))
print("progress: R99 closed=%s, +%d rows" % (closed,len(add)))

# --- PLAN
s=io.open(PLAN,encoding="utf-8").read()
a="| 进度分母 | **307 条 / 已结 223 / 72.6%** |"; b="| 进度分母 | **309 条 / 已结 229 / 74.1%** |"
assert a in s; s=s.replace(a,b,1)
BLOCK = """

### 八、R99 关闭（W1030）：S1 不是"慢"，是**算错**，而且在基准下 503

今天把 S1（`strata-0.1.57-003` = `exp/lcpp-b12169`=`7fdd5d3c`，b12129+#31047 自建 `tile_spec`）重新装上机跑了两道门，**随后自动回滚**（`trap restore`）：

| 门 | 做法 | 结果 |
|---|---|---|
| 门1 数值 | 48-token 贪心指纹，与 b11062 基线逐字节比 | **三例全不同**：en2k 224/224 但在**第 59 字符**分叉（旧 `User provided repeated sentence` / 新 `User provided many repetitions of pangram`）；short 118/122；zh2k 7/5 |
| 门2 速度 | `cfg_apply --record-only --n 6 --lengths 2000,8000` | **2K 直接 HTTP 503**；此前 968-token prompt 用了 **5.92 s**（含 48 token 生成），远慢于现役 |

判读：分派数据（`tile_spec`）形状错 ⇒ kernel 把列算到了错误的专家上 ⇒ 输出分叉。这不是数值噪声，也不是"上游优化不适用"，
**是我写的 spec 生成与上游语义不等价**。按 §6.6 写死的死法第一条「门1 不过 = spec 错，禁止进 S2」，以及"两轮修不好即关闭"：
**R99 → DONE_NEG**（`P374`）。收益预期本来就只有 2K prefill 的 8.3%（算术），而正确性代价是"错而不报错"。

**同时更正一条旧结论**：W1027 记的「S1 在 75-token 上 hang」**不可复现**——今天同一二进制 67/154/555 token 分别 1.51/1.79/2.50 s 正常返回、restarts=0（`P375`）。
当时大概是刚启动后的首个请求撞上了忙等。真正的缺陷是**算错**，比 hang 更难发现。

保留物：`exp/lcpp-b12169` = `7fdd5d3c`（分支不动）、`strata-0.1.57-003`（二进制）、`build-lcpp`（构建目录），
将来若有人把 spec 语义对齐上游，从这里起步；`R99` 的死因写在账本里，不是"效果不好"。
"""
if "R99 关闭（W1030）" not in s:
    s = s.rstrip("\n") + BLOCK
io.open(PLAN,"w",encoding="utf-8",newline="\n").write(s)
print("plan updated")
