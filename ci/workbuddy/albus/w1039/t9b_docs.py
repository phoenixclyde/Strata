import io
import re

# ---- ledger: record the downtime of gate #2
P = "deploy/PROGRESS.tsv"
s = io.open(P, encoding="utf-8").read()
i = s.find("\tP456\t")
j = s.find("\n", i)
row = s[i:j]
if "690 s" not in row:
    row2 = row + " 本窗口**停机 690 s**（10:49–11:00，三臂独占 GPU）。"
    s = s[:i] + row2 + s[j:]
    io.open(P, "w", encoding="utf-8", newline="\n").write(s)
    print("P456 downtime recorded")

# ---- report §三
R = "albus/w1039/reply.md"
t = io.open(R, encoding="utf-8").read()
OLD = """| ⑤ 数值门正式 | 10:18–10:29 | 1 次 | 683 s |

**前三窗口合计 重启 6 次 / 停机 264 s（129+135）**；救法窗口 重启 2 次 / 停机 90 s；数值门两次 重启 1+1 次 / 停机 52 s + **683 s**
⇒ 本回合合计 **重启 10 次 / 停机 1089 s / 回滚 0 次 / 装机 0 次**。最长单次停机 **683 s**（数值门三臂独占 GPU）。"""
NEW = """| ⑤ 数值门正式（int8） | 10:18–10:29 | 1 次 | 683 s |
| ⑥ 数值门（fp16） | 10:49–11:00 | 1 次 | 690 s |

**前三窗口合计 重启 6 次 / 停机 264 s（129+135）**；救法窗口 重启 2 次 / 停机 90 s；两个数值门 重启 1+1 次 / 停机 52 s + **683 s** + **690 s**
⇒ 本回合合计 **重启 11 次 / 停机 1779 s / 回滚 0 次 / 装机 0 次**。最长单次停机 **690 s**（数值门三臂独占 GPU）。"""
if OLD in t:
    t = t.replace(OLD, NEW, 1)
    print("report §三 updated")
io.open(R, "w", encoding="utf-8", newline="\n").write(t)

# ---- plan
PL = "deploy/W832_OPT_PLAN_V2.md"
u = io.open(PL, encoding="utf-8").read()
ADD = """
**十、fp16 查询的实测：预测被推翻（`P456`）。** pa6（`1ddc4ac9`）三臂数值门：地板仍 100.00%/0.00000；
`ATTN_F16D=1`（fp16 查询 + 4×`v_dot2_f32_f16`）得 **top-1 94.29% / KL 0.03798**，而 int8 那条是 93.55%/0.04130 ——
**q 精度差 40 倍、KL 几乎一样 ⇒ 误差不来自查询量化**。`P454` 的「int8 步长落在 0.19 nat 判决线上」归因**已撤回**。
两条 OPT 路径共有、基线没有的差异只剩三处：K 侧手写索引 vs `load8<KV_MODE>()`、`acc*ks` 一次乘 vs 逐元素乘、
以及 swizzle 的读法。**下一步（`P457`）按这个顺序分层剥离，直到 KL 归零**——若归零，锅在手写索引，
那是能修的，位宽不能修。
"""
anchor = "**纪律**：先编 → **先过数值门** → 再测速度；`P453` 的教训就是先测速度再补数值，白烧一个窗口。"
i2 = u.find(anchor)
if i2 > 0 and "**十、fp16 查询的实测" not in u:
    k = u.find("\n---", i2)
    u = u[:k] + "\n" + ADD + u[k:]
    print("plan §十 appended")
u = re.sub(r"\*\*\d+ 条 / 已结 \d+ / [\d.]+%\*\*（W1039 校正", "**399 条 / 已结 313 / 78.4%**（W1039 校正", u, count=1)
io.open(PL, "w", encoding="utf-8", newline="\n").write(u)

# ---- memory
M = ".workbuddy/memory/2026-11-07.md"
ADD2 = """
### W1039 T9（10:45–11:00）fp16 点积的数值门：假设被自己推翻

- pa6（`1ddc4ac9`/43,544,888 B）新增 OPT bit3 = **fp16 查询 + 4×`v_dot2_f32_f16`**（k 仍 int8，scale 末尾乘），env `STRATA_GFX906_ATTN_F16D=1`。
- 三臂（`--kv k8v4`，4995 点）：地板 A/Ab **100.00% / KL 0.00000**；A/B **top-1 94.29% / KL 0.03798 / PPL 4.080**。
- **预注册预测 KL <0.001，实测 0.038（差 38 倍）**；而 int8 是 0.04130 ⇒ **q 精度差 40 倍、KL 几乎不变 ⇒ 误差不是查询量化**。
- **`P454` 的「int8 步长压在 0.19 nat 判决线上」归因已撤回**（margin 数据仍有效，机理错）。两条 OPT 路径共有差异只剩：K 侧手写索引 vs `load8<>`、`acc*ks` 一次乘、swizzle 读法。
- 下一步 `P457`：把 K 换成 `load8<3>()` 的浮点通道再跑门；归零就说明锅在手写索引（可修），不是位宽。
- 教训：**预测先写进账本，再跑**——这次能立刻判定"被推翻"，不是事后讲故事。
"""
with io.open(M, "a", encoding="utf-8", newline="\n") as fh:
    fh.write(ADD2)
print("memory appended")
