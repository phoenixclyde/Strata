import io
import re

# ---------------- ledger ----------------
P = "deploy/PROGRESS.tsv"
ROWS = [dict(
    block="B6判定探针", id="P456",
    item=("fp16 查询 + `v_dot2_f32_f16` 的数值门：top-1 **94.29%** / KL **0.03798** —— 与 int8 的 93.55%/0.04130 几乎相同，"
          "**「误差来自 int8 步长」的假设被自己的实验推翻**"),
    source="W1039", kind="count", count="1", done="1", status="DONE_NEG",
    note=("**W1039 数值门 #2（pa6 = `1ddc4ac9` / 43,544,888 B；三臂同 `gate.sh`，`--kv k8v4`，4995 点）**。"
          "臂 A = pa6 无开关；Ab = 同 argv 第二容器；B = `STRATA_GFX906_ATTN_F16D=1`（OPT bit3 = fp16 q + 4×fdot2 + 末尾乘 ks）。"
          "**地板 A vs Ab：top-1 100.00% / KL 0.00000 / PPL 4.048** ⇒ 仪器仍然确定。"
          "**A vs B：top-1 94.29% / KL 0.03798（p99 0.6296）/ PPL 4.080 vs 4.048**。"
          "**预注册的预测是 KL <0.001（q 用 f16，误差 0.03% 对 int8 的 1.3%）——实测 0.038，差 38 倍，预测被推翻。**"
          "**这条证据的价值在于排除**：两条 OPT 路径（int8 与 fp16）QL/精度差 40 倍，KL 却几乎一样（0.0413 vs 0.0380）⇒ "
          "**误差不来自查询量化**，而是两条路径**共有**的某个差异（相对基线 `attn_chunk_kernel<M,false,true,true,0>`）。"
          "`P454` 的 margin 分析（322 个变动、234 个是第一名掉到第二名、间隔 p50 0.191 nat）仍然成立，但当时把它归因到「int8 步长落在判决线上」**已撤回**。"
          "**下一步已设计（`P457`）**：把 K 侧也换成基线的 `load8<KV_MODE>` 浮点通道，逐层剥离，直到 KL 归零为止。"),
    ref="P453;P454", kw="KW:94.29|推翻"),
]
s = io.open(P, encoding="utf-8").read()

# retract P454's attribution
i = s.find("\tP454\t")
assert i > 0
j = s.find("\n", i)
row = s[i:j]
if "已撤回" not in row:
    row2 = row + (" **W1041 撤回归因（见 `P456`）**：fp16 查询（误差小 40 倍）得到 KL 0.03798 ≈ int8 的 0.04130 ⇒ "
                  "「int8 步长落在 0.19 nat 判决线上」这个归因**不成立**；margin 数据本身仍然有效，但误差来源是两条 OPT 路径**共有**的差异，未定位。")
    s = s[:i] + row2 + s[j:]
    print("P454 attribution retracted")

add = []
for r in ROWS:
    if ("\t" + r["id"] + "\t") in s:
        print("skip", r["id"]); continue
    add.append("\t".join([r["block"], r["id"], r["item"], r["source"], r["kind"], r["count"], r["done"],
                          r["status"], r["note"], r["ref"], r["kw"]]))
if add:
    if not s.endswith("\n"):
        s += "\n"
    s += "\n".join(add) + "\n"
    print("ledger +", [a.split("\t")[1] for a in add])
io.open(P, "w", encoding="utf-8", newline="\n").write(s)

# ---------------- report ----------------
R = "albus/w1039/reply.md"
t = io.open(R, encoding="utf-8").read()

OLD = """**为什么还没有直接上**：它要新增一条 OPT 分支（共享 half 查询 tile + k 侧 i8→f16 打包 + 两个 score 分支各一份），
改错一处就是一次白烧的窗口。所以这一步按项目纪律走：**先编、再数值门、最后才测速度**；顺序不跳。"""
NEW = """**为什么还没有直接上**：它要新增一条 OPT 分支（共享 half 查询 tile + k 侧 i8→f16 打包 + 两个 score 分支各一份），
改错一处就是一次白烧的窗口。所以这一步按项目纪律走：**先编、再数值门、最后才测速度**；顺序不跳。

### T9 实测：预测被推翻（`P456`）

pa6 编好了（`1ddc4ac9` / 43,544,888 B），三臂数值门跑完：

| 臂 | top-1 | KL | KL p99 | PPL |
|---|---|---|---|---|
| A vs Ab（地板） | **100.00%** | **0.00000** | 0.0000 | 4.048 / 4.048 |
| A vs B（`ATTN_F16D=1`，fp16 查询） | **94.29%** | **0.03798** | 0.6296 | 4.080 / 4.048 |

**预注册的预测是 KL <0.001，实测 0.038——差 38 倍。** 而 int8 那条是 0.04130。**q 的精度差 40 倍，KL 几乎一样。**

**⇒ 误差不来自查询量化。** 两条 OPT 路径（int8/fp16）共有、而基线没有的那个差异，才是真凶。
`P454` 里"int8 步长落在 0.19 nat 判决线上"的归因**已撤回**（margin 数据仍然有效，错的是我给的机理）。

### T10 下一步：分层剥离，直到 KL 归零（`P457`）

怀疑对象按"两条 OPT 路径共有"这一条筛，只剩三处：

| # | 共有差异 | 怎么单独验 |
|---|---|---|
| 1 | K 侧走 `p.k_q`/`p.k_scale` 手写索引，而基线走 `load8<KV_MODE>()` | 把 F16D 的 K 换成 `load8<3>(...)` 取 float，再转 half；**若 KL 归零 ⇒ 索引错** |
| 2 | `acc*ks` 一次性乘 vs 基线逐元素 `c[j]*sc` | 同上一步顺带验（用 load8 就没有这一步） |
| 3 | 两条路径都不写 `sq` 的 swizzle、直接读自然序 | 把 `QUERY_SWIZZLE=false` 的实例化拉出来对拍（`<M,false,false,true,O>`） |

先做 ①，一次编译 + 一次数值门就能定；若归零，那 0.04 就是**我们手写索引**的锅（而不是任何指令），
这条路反而更好救——索引是可以修的，位宽不能。"""
if OLD in t and "### T9 实测：预测被推翻" not in t:
    t = t.replace(OLD, NEW, 1)
    print("report T9/T10 updated")
t = re.sub(r"\*\*\d+ 条 / 已结 \d+ / [\d.]+%\*\*（本轮 \+11：`P445`–`P455`）",
           "**399 条 / 已结 313 / 78.4%**（本轮 +12：`P445`–`P456`）", t, count=1)
io.open(R, "w", encoding="utf-8", newline="\n").write(t)
print("report denominators updated")
