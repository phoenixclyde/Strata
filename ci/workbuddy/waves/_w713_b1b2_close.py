# B1b 收口落盘：register 的 P10 evidence + 方案 §5（三臂矩阵/答案测试/判定）+ §6 账本 + 日志
import collections, hashlib, io, os, shutil, time

WS = r"D:/workbuddy_space/strata_ws"
REG = os.path.join(WS, "deploy", "params", "PARAM_REGISTER.tsv")
BAN = [0x21D2, 0x2192, 0x2014, 0x2013, 0x2026, 0x2265, 0x2264, 0x2260, 0x2212, 0x00D7]

# ---------- 1) register P10 的 evidence 追加（不改值/状态；仍 35/16-12-7）----------
raw = open(REG, "rb").read()
shutil.copy2(REG, REG + ".bak_w713b1b_" + time.strftime("%Y%m%d_%H%M%S"))
lines = raw.decode("utf-8").splitlines()
hdr = lines[0].split("\t")
IE = hdr.index("evidence")
APP = ("W713 B1b-2 收口（0.1.41，三臂 x 三档，Z0=off）：chunk=4096+every=4096 使 4.6k 会话温 TTFT 10.41 -> 3.06 s（-70.6%）、"
       "23.9k 温 16.85 -> 9.07 s，但**冷预填变差** 49.74 -> 55.06 s（-11%）/ 4.6k 10.39 -> 12.78 s（-23%）；chunk=2048 更差（23.9k 冷 67.83 s）。"
       "**并实测会改答案**：同一批固定 prompt 贪心（temp 0/top_k 1）跑，6,831-token 段 A(auto/8192) 与 C(2048) 得 md5 8b877ab2(len 336)、"
       "**B(4096) 得 9ffd3df2(len 338)**；1,430 与 18,078 两段三臂一致。=> chunk 是**会改答案的旋钮**（2048 在三段上恰好与 8192 一致，"
       "但仅 3 样本、不构成安全证明）。另：<4,096 的极短会话三臂一律 reused=0（chunk 机制盲区，与版本无关）。")
n = 0
out = []
for ln in lines:
    if ln.strip() and ln.split("\t")[0] == "P10":
        c = ln.split("\t")
        assert c[hdr.index("status")] == "ADOPTED" and c[hdr.index("value")] == "auto", "P10 形态变了"
        assert "B1b" not in c[IE], "P10 evidence 已含 B1b"
        c[IE] = c[IE] + " " + APP
        ln = "\t".join(c); n += 1
    out.append(ln)
assert n == 1, "P10 命中 %d" % n
io.open(REG, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
raw2 = open(REG, "rb").read()
rows = [l for l in raw2.decode("utf-8").splitlines() if l.strip()]
st = collections.Counter(r.split("\t")[hdr.index("status")] for r in rows[1:])
print("register md5 %s -> %s  行=%d status=%s CR=%d BAN=%d"
      % (hashlib.md5(raw).hexdigest()[:12], hashlib.md5(raw2).hexdigest()[:12], len(rows) - 1, dict(st),
         raw2.count(b"\r"), sum(1 for c in raw2.decode("utf-8") if ord(c) in BAN)))

# ---------- 2) 方案 §5 换新版（含答案测试与判定）----------
PLAN = os.path.join(WS, "deploy", "W713_PLAN.md")
t = io.open(PLAN, encoding="utf-8").read()
head = "## 5 附：B1b 首轮结果（0.1.40.4，2026-10-08 21:59-22:1x，Z0=off）"
i = t.find(head)
assert i > 0, "§5 标题未找到"
NEW5 = """## 5 附：B1b 结论（已在 0.1.41 上收口，2026-10-08 22:44-23:00，Z0=off）

三臂 x 三档矩阵（0.1.41 / 容器 -405；臂末断言 `/proc` 实际值；档内 2 轮）：

| 档（PARAS 段数） | **A: `auto`/8192（现役）** | **B: `4096`/4096** | **C: `2048`/2048** |
|---|---|---|---|
| 25（~1,210 tok） | 4.57 -> 4.607 s，`0` | 4.57 -> 4.570 s，`0` | 4.62 -> 4.581 s，`0` |
| 100（~4,59x tok） | 10.39 -> **10.413 s**，`0` | 12.78 -> **3.059 s**，`reused=4096` | 14.41 -> **2.978 s**，`reused=4096` |
| 530（~23,94x tok） | 49.74 -> **16.846 s**，`16384` | **55.06** -> **9.068 s**，`20480` | **67.83** -> 5.315 s，`22528` |

（与 0.1.40.4 那轮同口径：B-100 12.65 -> 3.593、B-530 55.70 -> 9.240 => 趋势未变，0.1.41 上温 TTFT 略更好。）

**答案是否变（本波新做的判据，原方案漏项）**：同一批固定 prompt、贪心（`temp 0`/`top_k 1`）、每段一次，
每臂把生成文本落盘比 md5：

| 段 | prompt | A（现役） | B（4096） | C（2048） |
|---|---|---|---|---|
| 0 | 1,430 tok | `4b040edc` len 347 | `4b040edc` len 347 | `4b040edc` len 347 |
| 1 | **6,831 tok** | `8b877ab2` **len 336** | `9ffd3df2` **len 338** | `8b877ab2` len 336 |
| 2 | 18,078 tok | `dbd09331` len 355 | `dbd09331` len 355 | `dbd09331` len 355 |

=> **`--prefill` 是会改答案的旋钮**：B（4096）在 6,831-token 段上连长度都变了。C（2048）这三段恰好与现役一致，
**但只有 3 个样本，不构成"安全"的证明**。（与 0.1.41 那条 CPU 助算"改答案末位"同性质。）

**判定（三条一起摆）**：
1. **收益真实**：4.6k 会话温 TTFT **10.41 -> 3.06 s（-70.6%）**；23.9k 温 16.85 -> 9.07 s。对多轮增长式会话是约 2 倍量级（5 轮 4.6k：约 52 s -> 约 25 s）。
2. **代价真实**：**冷预填变差** 23.9k 49.74 -> 55.06 s（-11%）、4.6k 10.39 -> 12.78 s（-23%）；一次性长文档是净亏。
3. **答案会变**（上面实测）=> 作为**基线参数**（P10）改动，等同于让每一条回复都换数值路径，**当前不建议采纳**。
4. 盲区未解：`<4,096` 的极短会话三臂一律 `reused=0`（chunk 机制所限，换任何值都无效）。

**处置**：**不改基线 P10**；本结论已写进 register **P10 的 evidence**（值/状态不动，仍 35 行 / 16-12-7）。
若机主要拿这 70% 的短会话提速，可**单独选时段**临时切（脚本 `switch_strata.sh` 不涉及参数；改 `--prefill` 仍须走 register 通道）。
**更干净的替代路径（建议）**：向上游提 feature request ---- 让可复用 checkpoint 落在**子 chunk 边界**而不改 prefill chunk，这样既不换数值路径、又能补上短会话盲区。
"""
t = t[:i] + NEW5
io.open(PLAN, "w", encoding="utf-8", newline="\n").write(t)
print("§5 已换新版（%d 字节）" % len(t))

# ---------- 3) §6 账本：#3 标完成 ----------
t = io.open(PLAN, encoding="utf-8").read()
O = "| 3 | **B1b 收口**：① 答案是否变 ② 0.1.41 上复核 ③ 冷预填代价入结论 | 动的是**基线 P10**，不齐三项不采纳 |"
N = "| ~~3~~ | ~~**B1b 收口**~~ **已完成 23:00**：①答案**会变**（B 臂 6,831 段连长度都变）②已在 0.1.41 复核（趋势未变）③冷预填代价 -11%~-23% 已入结论 => **不改基线 P10** | 见 §5 与 register P10 evidence |"
assert t.count(O) == 1, "§6.2#3 锚点未命中"
io.open(PLAN, "w", encoding="utf-8", newline="\n").write(t.replace(O, N))
print("§6.2#3 已标完成")

# ---------- 4) 日志 ----------
log = os.path.join(WS, ".workbuddy", "memory", "2026-10-08.md")
io.open(log, "a", encoding="utf-8", newline="\n").write("""
## W713e B1b 收口（2026-10-08 22:44-23:00，引擎 0.1.41 / 容器 -405）
- 三臂（auto/8192 · 4096/4096 · 2048/2048）x 三档（25/100/530）+ **答案一致性探针**（新写 `deploy/data/bench_answer.py`：同批固定 prompt、
  贪心 temp0/top_k1、3 段长度 1,430 / 6,831 / 18,078，每臂落盘比 md5）。收尾无条件恢复生产 config（md5 复原、引擎回 auto/8192）。
- 矩阵（0.1.41）：A 100 档 10.39 -> 10.413（reused 0）；B 12.78 -> **3.059**（4096）；C 14.41 -> 2.978（4096）；
  A 530 49.74 -> 16.846（16384）；B **55.06** -> 9.068（20480）；C **67.83** -> 5.315（22528）。趋势与 0.1.40.4 一致。
- **答案测试（关键发现）**：段0 三臂同 `4b040edc`；**段1（6,831）A/C = `8b877ab2` len336，B = `9ffd3df2` len338 => B 改了答案**；
  段2 三臂同 `dbd09331`。=> **`--prefill` 是会改答案的旋钮**（C 三段恰好一致但仅 3 样本，不算安全证明）。
- **判定：不改基线 P10**（收益真实 -70.6% 温 TTFT / 代价真实 冷预填 -11~-23% / **答案会变**，三条一起摆）。
  结论写进 register **P10 evidence**（值/状态不动，仍 35 行 / 16-12-7；`gen_config --write` 后生产 config 应逐字节未变）。
  替代建议：向上游提 feature request（可复用 checkpoint 落子 chunk 边界而不改 prefill chunk）。
- 证据：`deploy/tmp/_w713_b1b2_remote.log`（166 `w712/b1b2.log` 全文）；脚本 `deploy/scripts/_w713_b1b2.sh`（md5 752c75e10d0fff15630790c5e75dc449）、
  探针 `deploy/data/bench_answer.py`（md5 97e0a40a2672ba257fe083fa666ea512）。
""")
print("日志已追加")
