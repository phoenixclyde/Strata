import io

P = "deploy/PROGRESS.tsv"
ROWS = [
    dict(block="B6判定探针", id="P454",
         item=("数值门 6.45% 的真相：322 个 argmax 改动里 234 个是「第一名掉到第二名」，"
               "参考侧判决间隔中位 **0.191 nat**，Δlogp 中位 0.018 ⇒ 扰动恰好落在分岔口，不是答案错"),
         source="W1039", kind="count", count="1", done="1", status="DONE",
         note=("**W1039 逐点对齐（`margin_analysis.py` 读 run_A.tsv / run_B.tsv，4995 点）**：argmax 变化 **322/4995 = 6.45%**；"
               "其中 **234（72.7%）** 是 A 的第一名在 B 里落到第 2 位（B 的 top-64 里 234 个 rank=2、48 个 rank=3、0 个出 64 之外仅 1 个）；"
               "改动处的参考间隔（top1−top2）p10 **0.025** / p50 **0.191** / p90 1.055 / p99 3.96 nat；"
               "间隔 <0.1 nat 的占改动 32%、<0.5 nat 占 75%；|Δlogp(target)| 中位 **0.018**、p90 0.402。"
               "**机制**：int8 查询步长 = 组内 amax/127 ⇒ RMS ≈0.45%×amax ≈ **1.3%×σ_q**；分数是 256 维点积 ⇒ 相对误差 ~1.3% ⇒ 对 O(1–10) 的分数就是 0.01–0.13 nat，与观测的 0.018/0.191 同量级。"
               "**⇒ 8 bit 的步长正好压在模型做决定的间隔上，不是实现缺陷。** 项目标尺要 KL ≤0.0139 = 噪声再小 3 倍，单档 int8 不可能（步长与位宽指数相关）。"),
         ref="P453", kw="KW:0.191|分岔"),
    dict(block="B6判定探针", id="P455",
         item=("可行救法：把这一层从 int8 换成 **fp16 点积 `v_dot2_f32_f16`** —— 每 8 MAC 仍是 5 条指令（与 int8 同）"
               "但 q 误差从 1.3% 降到 0.03%，预计 KL <0.001；工具链已验证可编（CLANG=0）"),
         source="W1039", kind="count", count="1", done="0", status="OPEN",
         note=("**W1039 立（`P454` 的必然下一步）**。算式：`v_dot2_f32_f16` = **2 MAC/指令**，8 个 MAC 只要 4 条；"
               "k 侧 int8→f16 **精确**（|k|≤127 在 f16 里无损），scale 放到最后乘 ⇒ 每头 = 4 dot2 + 1 mul = **5 条，与 int8 路径相同**；"
               "而 q 用 f16（2^-11 = 0.049%，RMS 0.03%）⇒ 比 int8 的 1.3% 小 **40 倍**，KL 按噪声平方估 <0.001。"
               "**外证**：同代卡 `__builtin_amdgcn_fdot2 -> v_dot2_f32_f16`，摊薄复用 21.9 TOPS vs fp32 13.0（skyne98 实测）。"
               "**本地验证**：`__builtin_amdgcn_fdot2(__half2,__half2,float,false)` 在 `--offload-arch=gfx906` 下编译通过（`tmp/w1041/t_fdot2.cu`，CLANG=0，7,768 B）。"
               "**实现面**：新增 OPT bit 3（值 8）= 共享 half 查询 tile（12×256×2 B = 6 KB）+ k 侧 i8→f16 打包（12 头共用）+ 两个 score 分支各一份；dispatch 加 case 8/9。"
               "**纪律**：先编 → **先过数值门** → 再测速度，不跳步（`P453` 的教训就是先测速度再补数值，白烧一个窗口）。"
               "**判据**：KL ≤0.0139 且 top-1 ≥99%；过了才进速度窗，速度目标「attn 不劣于 −8%」。" ),
         ref="P454;P453", kw="KW:v_dot2_f32_f16|40倍"),
]
s = io.open(P, encoding="utf-8").read()
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
    io.open(P, "w", encoding="utf-8", newline="\n").write(s)
    print("ledger +", [a.split("\t")[1] for a in add])
