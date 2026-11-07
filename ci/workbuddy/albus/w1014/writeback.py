import io

PLAN = "deploy/W832_OPT_PLAN_V2.md"
PROG = "deploy/PROGRESS.tsv"
BUNDLE = "ci/bundle_budget/BUNDLE.tsv"

# ---------- 1. BUNDLE.tsv: v3 measured end-to-end, so it leaves the blocked list ----------
b = io.open(BUNDLE, encoding="utf-8").read()
b = b.replace("B1\tR21-v3hc\tv3 read needs an int8-code kernel (ours are HC_Q8)\thc read: down+silu\t117\t-40.0\t6.0\testimate\tN\tBLOCKED\tci/prefill_phases/PREFILL_PHASES.tsv",
              "B1\tR21-v3hc\tv3 read with HC_Q8=0: measured, 0.4% and a regression at 8K\thc read: down+silu\t117\t-40.0\t6.0\testimate\tN\tREJECTED\tci/state/cfg/w1014-v3on.json")
b = b.replace("B1\tR98-wc\twait-copy prefetch depth\twait copy\t37\t-50.0\t8.0\testimate\tY\tREJECTED\tci/prefill_phases/PREFILL_PHASES.tsv",
              "B1\tR98-wc\tring 384 -> 768: measured, 0.5-0.6% SLOWER at all three lengths\twait copy\t37\t-50.0\t8.0\testimate\tY\tREJECTED\tci/state/cfg/w1014-ring768.json")
io.open(BUNDLE, "w", encoding="utf-8", newline="\n").write(b)

# ---------- 2. bundle.py: the candidate sum is the number that matters, not "all rows" ----------
q = "ci/bundle_budget/bundle.py"
s = io.open(q, encoding="utf-8").read()
if "candidates (CANDIDATE)" not in s:
    s = s.replace('''            universe = sum(it["e2e"] for it in per[b])
            print("   -> measured sum %+.2f%% ; estimates on top %+.2f%% ; every row together %+.2f%% ; gate -%.1f%%"
                  % (adopted.get(b, 0.0), estimates.get(b, 0.0), universe, GATE))''',
'''            universe = sum(it["e2e"] for it in per[b])
            cands = sum(it["e2e"] for it in per[b] if it["status"] == "CANDIDATE")
            print("   -> measured sum %+.2f%% ; estimates on top %+.2f%% ; candidates (CANDIDATE) %+.2f%% ;"
                  " every row %+.2f%% ; gate -%.1f%%"
                  % (adopted.get(b, 0.0), estimates.get(b, 0.0), cands, universe, GATE))''')
    io.open(q, "w", encoding="utf-8", newline="\n").write(s)

# ---------- 3. the plan block ----------
BLOCK = '''
### 回写 · W1014（把「去掉 HC_Q8 比过吗」测了：三条都测过，R21 与 R98 从算术否决升级为实测否决）

W1013 判 R21 时只证明「v3 在我们配置下不执行」，**没有测「去掉 `STRATA_HC_Q8` 让它执行」**——机主当场追问
的就是这一条。本轮补三臂，全部 `cfg_apply` 冷 prompt、n=6/3、逐长度带：

| 臂 | env | prefill@2000 | @8000 | @16000 | 判 |
|---|---|---|---|---|---|
| 基线 | — | 513.65 tok/s | 684.62 | 767.22 | — |
| **B 去 HC_Q8** | `HC_Q8=0` | 513.47（**−0.04%**） | 685.81（+0.17%） | 765.21（−0.26%） | REVERT（三档全在带内） |
| **C 去 HC_Q8 + v3** | `HC_Q8=0,GR_V3=1` | 511.64（**−0.36%**） | 683.46（**−0.34%**，band 0.20） | 767.12（+0.25%） | ROLLBACK |
| **D 加深 ring** | `PREFILL_RING=768` | 510.94（**−0.53%**） | 680.43（**−0.61%**） | 763.03（**−0.55%**） | ROLLBACK |

三条都是实测，结论各自不同：

1. **`STRATA_HC_Q8` 在速度上是免费的**（−0.04 / +0.17 / −0.26%，全在带内）。它买的是**比特**
   （KL 0.0011、argmax 100%）不是吞吐 ⇒ 「去掉它换 v3」在算术上不吃亏，这个前提成立。
2. **v3 真跑了也没用**：C 臂 vs B 臂 = −0.36 / **−0.34** / +0.25%，net vs 基线 = −0.39 / −0.17 / −0.01%。
   与上游自己的注释一致（`fused_gr.cu:2653`：A4000 −3.0/−5.9%、3060 +1.0/−3.4%，只有 sm_120 是正的）。
   ⇒ **R21 现在是实测否决**，不再只是「永不执行」的源码推论。
3. **R98 的「先量后动」补上了**：ring 384→768 在三个长度上一致地慢 **0.5–0.6%**（两条超带），
   说明 37 ms 的 `wait copy` **不是靠加深预取能省的**，加深只是多占槽、挤缓存。⇒ **R98 实测否决**，
   而且是「反向」的：越深越慢。这一条也解释了 W1013 的算术估计（−0.58% 天花板）为什么不成立——**符号是反的**。

**组合预算随之收缩**：`R21`、`R98` 由 BLOCKED/算术拒 转为实测拒后，BUNDLE 里只剩两条 CANDIDATE ——
`R86-dn −3.20%`（bench）+ `R95-plan −2.85%`（estimate），**候选合计 −6.05%，其中实测只有 −3.20%**。
`bundle.py` 现在同时打印 candidates 与 all-rows 两个和，避免「把已否决的行也算进未来」。

**外网补一条硬依据（举一反三）**：gfx906 的实测 dot 吞吐——`sdot4` 21.7–22.3 TOPS（链式）/ 43–44 TOPS（ILP4），
`sdot8` 43.5–44.4 / 85–86 TOPS，FP32 峰值 13.4 TFLOPS（热路径 5.95 TOPS）；**`v_mfma*` 根本不在 gfx906 的指令表上**
（只有 gfx908+）。这与 `W863_PARAM_COMBO §1` 已判的 R35（HC 的 dp4a：548 vs 673 µs，慢 15–23%）一致 ⇒
「给 v3 写 int8 版」这条路**两头都堵**：v3 要 bf16 行，而 int8 走 dp4a 又比 fma 慢。R21 的三个死因齐了。
'''
s = io.open(PLAN, encoding="utf-8").read()
if "回写 · W1014" not in s:
    s = s.rstrip("\n") + "\n" + BLOCK
io.open(PLAN, "w", encoding="utf-8", newline="\n").write(s)

# ---------- 4. ledger ----------
ROWS = [
 ("B6判定探针", "P325", "`STRATA_HC_Q8=0` 在速度上免费（−0.04/+0.17/−0.26%，全在带内）", "W1014", "DONE",
  "**W1014 立**：`cfg_apply` 冷 prompt n=6/3，prefill@2000 513.47（−0.04%）、@8000 685.81（+0.17%）、@16000 765.21（−0.26%），三档全在带内 ⇒ 该开关买的是比特（KL 0.0011）不是吞吐。"
  "⇒ 「去 HC_Q8 换 v3」在速度上不吃亏，前提成立。",
  "ci/state/cfg/w1014-hcq8off.json"),
 ("B6判定探针", "P326", "v3 真跑也没用：`HC_Q8=0+GR_V3=1` vs `HC_Q8=0` = −0.36/**−0.34**/+0.25%", "W1014", "DONE_NEG",
  "**W1014 立**：C 臂（v3 实际启用，bf16 行）对 B 臂 @8000 **−0.34%**（band 0.20）超带、@2000 −0.36%（band 1.46）在带内、@16000 +0.25%；net vs 基线 −0.39/−0.17/−0.01%。"
  "与 `fused_gr.cu:2653` 上游自述一致（A4000 −3.0/−5.9%、3060 +1.0/−3.4%，只有 sm_120 正）。⇒ **R21 由「永不执行」的推论升级为实测否决**。",
  "ci/state/cfg/w1014-v3on.json"),
 ("B6判定探针", "P327", "R98 实测：ring 384→768 三档一致慢 0.5–0.6%（两条超带）⇒ 越深越慢", "W1014", "DONE_NEG",
  "**W1014 立**：`PREFILL_RING=768` 对基线，prefill@2000 510.94（−0.53%，band 0.78 在带内）、@8000 680.43（−0.61%，band 0.30 超带）、@16000 763.03（−0.55%，band 0.16 超带）。"
  "**符号与 W1013 的算术估计相反**（原估 −0.58% 收益）⇒ 37 ms 的 wait copy 不能靠加深预取省，加深只多占槽挤缓存。R98 实测否决。",
  "ci/state/cfg/w1014-ring768.json"),
 ("B4上游移植", "P328", "外网 gfx906 dot 实测：sdot4 21.7–22.3 TOPS / sdot8 43.5–44.4；`v_mfma` 不在 gfx906 指令表", "W1014", "DONE_NEG",
  "**W1014 立**：外部实测（4×gfx906，60 CU @1.725 GHz）`sdot4` 21.7–22.3 TOPS（链式）/ 43–44.4（ILP4），`sdot8` 43.5–44.4 / 85–86，FP32 峰值 13.4 TFLOPS（热路径 5.95）；"
  "`v_mfma*` 只出现在 gfx908+ 的指令表。⇒ GDN 分块在 gfx906 只能 FMA（P324 判据坐实），且「给 v3 写 int8 版」被 R35 的 548 vs 673 µs 挡住 ⇒ R21 三死因齐。",
  "ci/bundle_budget/BUNDLE.tsv"),
]
lines = io.open(PROG, encoding="utf-8").read().split("\n")
hi = next(i for i, l in enumerate(lines) if not l.startswith("#") and l.count("\t") >= 9)
head = lines[hi].split("\t")
ID, ST, NOTE = head.index("id"), head.index("status"), head.index("note")
have = {l.split("\t")[ID] for l in lines if l.count("\t") >= 9}
add = ["\t".join([blk, pid, item, src, "count", "1", "1", st, note, ref])
       for blk, pid, item, src, st, note, ref in ROWS if pid not in have]

notes = {
 "R21": "**W1013 源码 + W1014 实测双否**：`HC_Q8=1` 使 `split` 恒 −1（`fused_gr.cu:2899`），开关无效（prefill 三档 +0.08/+0.05/−0.08%）；去掉 HC_Q8 让它真跑，@8000 仍 **−0.34%**（超带）。三个死因（Q8 行 / dp4a 更慢 / 上游在 sm_86 也是负）齐。",
 "R98": "**W1014 实测否决**：`PREFILL_RING=768` 三档 **−0.53/−0.61/−0.55%**（两条超带）⇒ 越深越慢，37 ms 的 wait copy 不能靠深度省，W1013 的算术估计符号是反的。",
}
for i, l in enumerate(lines):
    if l.count("\t") < 9 or l.startswith("#"):
        continue
    c = l.split("\t")
    if c[ID] in notes:
        c[ST] = "DONE_NEG"
        c[NOTE] = notes[c[ID]]
        lines[i] = "\t".join(c)
if add:
    while lines and lines[-1] == "":
        lines.pop()
    lines += add + [""]
io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
print("plan block + %d rows + %d notes" % (len(add), len(notes)))
