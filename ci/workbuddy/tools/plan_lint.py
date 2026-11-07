r"""plan_lint.py —— 回溯"有没有待办没落进唯一方案"。

四个判据（任一不过就是漏洞；收工前必须 exit 0）：
  A. PROGRESS.tsv 里每条未结（OPEN/INFLIGHT/BLOCKED），其 id **或其 ID_MAP 映射** 必须在方案里出现；
  B. PARAM_REGISTER.tsv 里未结（OPEN/PENDING/CANDIDATE/UNRESOLVED/PARTIAL），同上；
  C. deploy/W8*.md 正文里"待办/下一步/未测/待测"等字样带的 id，必须在 PROGRESS 或登记表里有账；
  D. 反向：方案 §6.2/§6.5 列出的每个 R\d+ 必须在 PROGRESS 有对应行（否则就是"方案说要做，没人跟踪"）；
  E. deploy/ 下的 *PLAN*.md 只许有一份（W832），其余必须在 PLAN_FROZEN 里登记过角色。

ID_MAP.tsv 是唯一对照表（左=账本 id，右=方案锚点）。

用法: python tools/plan_lint.py [--quiet]
退出码: 0 = 全过；1 = 有漏洞。
"""
from __future__ import annotations

import glob
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEPLOY = os.path.join(ROOT, "deploy")
PLAN = os.path.join(DEPLOY, "W832_OPT_PLAN_V2.md")
PROGRESS = os.path.join(DEPLOY, "PROGRESS.tsv")
REGISTER = os.path.join(DEPLOY, "params", "PARAM_REGISTER.tsv")
IDMAP = os.path.join(DEPLOY, "ID_MAP.tsv")

# 2026-11-02 冻结：deploy/ 下只许 W832_OPT_PLAN_V2.md 是「方案」。
# 其余这些是历史件 / 证据件 / 已标 SUPERSEDED 的草稿，登记在此仅为了不再增长。
# 要新增方案 —— 写进 W832 §6.5，不要新开文件。
RX_SELF = re.compile(r"(SUPERSEDED|已冻结|已被取代|作废|不是方案|不构成队列|不是队列)")

PLAN_FROZEN = {
    "PLAN_PROGRESS.md",                 # 进度快照，非方案
    "W712_PLAN.md", "W713_PLAN.md", "W749_OPT_PLAN.md",
    "W750_MASTER_PLAN.md", "W756_UPSTREAM_BENCH_PLAN.md",
    "W776_TUNING_MASTER_PLAN.md", "W829_OPT_PLAN.md", "AUDIT15_PLAN.md",
    "W775delta_UPSTREAM_022_PLAN.md", "W775delta_UPSTREAM_LATEST_PLAN.md",
    "W775delta_W28D_OPT_PLAN.md",
    "W863_SINGLE_STREAM_PLAN.md",       # §0 已登记：证据与结论，不构成队列
    "W878_OPT_PLAN_V3.md", "W881_OPT_PLAN_V4.md", "W882_OPT_PLAN_V5.md",  # SUPERSEDED 草稿
    # W1002 补登记：这四份是证据/重排快照，不是活方案；V3.9 队列已回写 W832 §6.5。
    "W940_DOT4_DOT8_AND_PLAN_GAP.md",  # dot4/dot8 上限的实测与口径更正
    "W951_DOT8_PORT_PLAN.md",          # R91 dot8 移植的数值证据与判据
    "W954_PLAN_RERANK.md",             # 一次队列重排的快照（已被 V3.9 取代）
    "W986_PLAN_V3.md",                 # SUPERSEDED：V3.0-V3.9 历次修订留档
}

OPEN_STATES = {"OPEN", "INFLIGHT", "BLOCKED"}
REG_OPEN = {"OPEN", "PENDING", "CANDIDATE", "UNRESOLVED", "PARTIAL"}


def read(path):
    return io.open(path, encoding="utf-8", errors="replace").read()


def rows(path):
    for ln in read(path).splitlines():
        if not ln or ln.startswith("#"):
            continue
        yield ln.split("\t")


def main():
    quiet = "--quiet" in sys.argv
    plan = read(PLAN)
    prog = {f[1]: f for f in rows(PROGRESS) if len(f) >= 10}
    reg = {f[0]: f for f in rows(REGISTER) if len(f) >= 11}
    idmap = {}
    for f in rows(IDMAP):
        if len(f) >= 3 and f[0] != "src_id":
            idmap[f[0]] = f[2]

    bad = []

    def in_plan(token, ids):
        for t in ids:
            if re.search(r"(?<![\w.])%s(?![\w])" % re.escape(t), plan):
                return True
        return False

    a_open = [(i, f) for i, f in prog.items() if f[7] in OPEN_STATES]
    a_miss = []
    for i, f in a_open:
        ids = [i, f[9].strip()] + ([idmap[i]] if i in idmap else [])
        ids = [x for x in ids if x]
        if not in_plan(None, ids):
            a_miss.append(i)
            bad.append(("A", i, f[2][:60]))

    b_open = [(p, f) for p, f in reg.items() if f[5].strip() in REG_OPEN]
    b_miss = []
    for p, f in b_open:
        ids = [p] + ([idmap[p]] if p in idmap else [])
        if not in_plan(None, ids):
            b_miss.append(p)
            bad.append(("B", p, reg[p][2][:60]))

    kw = re.compile(r"(待办|下一步|未测|待测|未验证|尚未|候选|OPEN|PENDING)")
    # 同一行里已经声明"撤回/判否/结案"的，不是待办，别报（W882：W863 §10.4 的 R41 撤回记录曾被误报）
    kw_skip = re.compile(r"(撤回|已结|结案|判否|作废|DONE_NEG|SUPERSEDED)")
    # AUDIT27: R numbers went 3-digit at R99/R100/R101/R102; \d{1,2} made them invisible
    # to this gate ("D. 方案里的 R 号全部有人跟踪" was false from W1026 on).
    tok = re.compile(r"(?<![\w.])(R\d{1,3}|X\d{1,3}|M\d{1,3}|G\d{1,3})(?![\w])")
    c_miss = []
    for p in sorted(glob.glob(os.path.join(DEPLOY, "W8*.md"))):
        if os.path.basename(p).startswith("W830_"):
            continue
        for n, ln in enumerate(read(p).splitlines(), 1):
            if len(ln) < 12 or not kw.search(ln) or kw_skip.search(ln):
                continue
            for t in set(tok.findall(ln)):
                # 方案里的 R 号经 ID_MAP 反查账本 id
                rev = [k for k, v in idmap.items() if v == t]
                if t in prog or rev:
                    continue
                c_miss.append((os.path.basename(p), n, t))
    for f, n, t in c_miss:
        bad.append(("C", t, "%s:%d" % (f, n)))

    # D. 方案 §6.2/§6.5 的 R 号 → PROGRESS
    sec = plan[plan.index("### 6.2 "):plan.index("### 6.6 ")]
    # 已撤回/划掉的条目不再要求账本跟踪（W882：W832 §6.2 的 ~~R41~~ 曾被误报）
    sec_live = "\n".join(ln for ln in sec.splitlines()
                         if not re.search(r"(撤回|作废|DONE_NEG|~~)", ln))
    plan_r = sorted(set(re.findall(r"(?<![\w.])R(\d{1,3})(?![\w])", sec_live)), key=int)
    rev = {}
    for k, v in idmap.items():
        if v.startswith("R") and v[1:].isdigit():
            rev[v] = k
    d_miss = []
    for r in plan_r:
        key = "R" + r
        if key in prog or rev.get(key) in prog:
            continue
        d_miss.append(key)
        bad.append(("D", key, "方案有、账本无"))

    # E. deploy/ 下的 *PLAN*.md 只许有一份权威，其余必须是既有的历史/证据件（W882 立）
    #    A–D 都只比「W832 ↔ 账本」，对"另开一份新方案"零感知；2026-11-02 凌晨就是这样
    #    连开了 V3/V4/V5 三份，机器一声没响。这里把清单冻结：新出现的 *PLAN*.md 一律报错，
    #    要么写进 W832 §6.5，要么先在此登记并说明角色。
    seen, e_new = set(), []
    for pat in ("*PLAN*.md", "*plan*.md", "*ROADMAP*.md", "*QUEUE*.md"):
        for p in glob.glob(os.path.join(DEPLOY, pat)):
            b = os.path.basename(p)
            if b in seen:
                continue
            seen.add(b)
            if b == "W832_OPT_PLAN_V2.md" or b in PLAN_FROZEN:
                continue
            # 自证：头部 40 行内声明「作废/取代/不是队列」的放行（W785 就靠这个过）
            head = "\n".join(read(p).splitlines()[:40])
            if RX_SELF.search(head):
                continue
            e_new.append(b)
            bad.append(("E", b, "未登记的方案文件：方案只许有一份（W832 §6.5）"))

    # F. §6.5 的「回写/补记」小节里，通道标记（C1..C9）必须有号 —— W1003-c 立。
    #    当时的六通道表只有裸 C1..C6、正文还写「不新增 ID」，而 A–D 全绿：
    #    门只认识 R\d+，对「有内容、没编号」的表格零感知。判据：一个补记块里出现
    #    ≥2 个不同的裸 Cn，就必须同时出现该块的子号 R<父>-Cn。
    f_miss = []
    for blk in re.split(r"\n(?=#{2,3} §6\.5 (?:回写|补记))", plan)[1:]:
        bare = set(re.findall(r"(?<![\w-])C([1-9])(?![\w-])", blk))
        if len(bare) < 2:
            continue
        sub = set(re.findall(r"(?<![\w-])R\d{1,2}-C([1-9])(?![\w-])", blk))
        for c in sorted(bare - sub):
            f_miss.append(("C%s" % c, blk.splitlines()[0][:40]))
    for t, h in f_miss:
        bad.append(("F", t, "%s：通道标记无子号" % h))

    if not quiet:
        print("A. PROGRESS 未结 %d 条，方案未提 %d 条" % (len(a_open), len(a_miss)))
        for i, f in a_open:
            print("   [%s] %-4s %s" % ("MISS" if i in a_miss else "ok  ", i, f[2][:66]))
        print("B. 登记表未结 %d 条，方案未提 %d 条" % (len(b_open), len(b_miss)))
        for p, f in b_open:
            print("   [%s] %-5s %s" % ("MISS" if p in b_miss else "ok  ", p, f[2][:66]))
        print("C. 正文带 id 的待办：未入账 %d 处" % len(c_miss))
        for f, n, t in c_miss[:40]:
            print("   [MISS] %-34s:%-4d %s" % (f, n, t))
        print("D. 方案 §6.2/§6.5 的 R 号 %d 个，账本缺 %d 个：%s" % (len(plan_r), len(d_miss), ",".join(d_miss) or "-"))
        print("E. deploy/ 下 PLAN 文件 %d 份，未登记 %d 份：%s" % (len(seen), len(e_new), ",".join(e_new) or "-"))
        print("F. §6.5 补记里的通道标记无子号 %d 处：%s" % (len(f_miss), ",".join(t for t,_ in f_miss) or "-"))

    if bad:
        print("\n**plan-lint FAIL：%d 处漏洞**" % len(bad))
        return 1
    print("\n**plan-lint PASS：未结项全部在方案里，正文待办全部有账，方案里的 R 号全部有人跟踪，补记的通道标记都有子号**")
    return 0


if __name__ == "__main__":
    sys.exit(main())
