#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1040: land the round in the only two authoritative files (PROGRESS rows + W832 §0.1/§6.5)."""
import io, hashlib, os, re, shutil, time

ROOT = r"D:/workbuddy_space/strata_ws"
PROG = os.path.join(ROOT, "deploy", "PROGRESS.tsv")
PLAN = os.path.join(ROOT, "deploy", "W832_OPT_PLAN_V2.md")

# ---------------------------------------------------------------- PROGRESS rows
ROWS = [
 ("B9显存", "P490",
  "R104 装机落地：`--kv-grow` 进生产（引擎 `strata-0.1.57-kvg`，config 加 `--kv-grow`），专家槽 **7463 → 8301（+838 / +11.2%）**",
  "W1040", "count", "1", "1", "DONE",
  "**W1040 实测（窗口 14:10:03–14:14:38，停机 275 s，一次停/起）**。门：`tools/deploy_gate.py --exe strata-0.1.57-kvg --ab albus/w1040/ab_kvg.json --cfg-base/--cfg-new --reg-ids P32 --live` ⇒ **D1–D5 全 PASS**（D1 `a85743d7…` / 43,214,976 B；D2 53 件回滚制品；D3 容量型目标 7463→8301 且四条墙钟护栏全在带内；D4 逐位相同；D5 增量只有 exe + `--kv-grow`）。**改动面**：二进制 = `pr/k10 @ af797b90` + `vmm.cpp` 一处条件改 OR（`a85743d7f554159e8ac1e2d432d2e5ea`），config `5e9b81e2f66ca48999766d2ae0201fb6` → **`ee69ebc272ce41a116f50ecb3bf0edc2`**（1680 B，38 args）。**起机行（新日志切片）**：`expert cache 8301 slots, 24.23 GiB of VRAM`、`elastic K/V: 16384 of 262144 cells in VRAM (0.21 of 2.65 GiB)`，且**没有** `--kv-grow is off` 行（b12180 的还原块里也没有它，只有它才证明开关态）。**增长/归还实测**：`K/V grown to 24576/32768 cells`、`the expert cache gave 25–55 slots for it, 25–52 hotter experts moved to colder ones' slots`、`K/V trimmed to 8192 cells; 55/80 slots back to the expert cache, refilled from the profile`；无 `could not map`、无 `ERR the K/V could not give its VRAM back`。**数值**：见 `P495`/`P494`。**回滚**：`b12180` `d24f8293b575fbcee6c097239d9599cb` 仍在 `/data/bin`，config 备份 `tmp/w1040/cfg_w1040.bak`（逐字节 = `5e9b81e2`）。",
  "P474;P488;P489", "KW:8301|ee69ebc2|275"),
 ("B8工程", "P491",
  "装机门补上 **D5 配置面**，并把 D3 扩成「延迟型 / 容量型」两类目标：原工具文档写着六条判据、代码里只有五条（D5 从未实现）",
  "W1040", "count", "1", "1", "DONE",
  "**缺陷（源码核实）**：`tools/deploy_gate.py` 的 docstring 列 D1–D6，`main()` 里只有 D1/D2/D3/D4/D6 —— **「改参唯一道」这条从来没有被机械验过**，而它正是最容易静默失效的一条（config 手改一行，谁也看不出来）。**本轮的实现**：`--cfg-base/--cfg-new/--reg-ids`，判据是**增量**而非 md5 相等 —— 新 config 除 `exe`（制品指针）外，只能多出本轮 ADOPTED 的 register 行声明的 CLI flag / ENV 名，其余键逐项相同，少了任何键也拒。**为什么不判 md5 相等**：`gen_config` 今天产出的 config 与生产有 9 处差异（`P492`），照它推生产会丢 `STRATA_GFX906_TUNED=1`。**D3 容量型**：目标量可以是整数计数（槽数，零方差），此时墙钟降级为护栏（`|Δ| <= 2×CV`），仍逐点判。**自检**：本轮真实用例 PASS（`args +--kv-grow（来自 P32）`），把 `--reg-ids` 换成空则 REFUSE —— 判据不是摆设。",
  "P490", "KW:D5|增量门|容量型"),
 ("B8工程", "P492",
  "`gen_config` 与生产 config 有 **9 处漂移**：4 个在用的 env 根本没登记成 ENV、3 个 ENV 行的 name/value 混进注释文字、tokenizer/model_name 过期 ⇒ 立 `R106`",
  "W1040", "count", "1", "0", "OPEN",
  "**实测（`python deploy/params/gen_config.py --live`）**：生成侧比生产**多** `STRATA_GFX906_ATTN_QUERY_SWIZZLE`（值写成 `1(在 k8v4 下不可达;W775delta 改判)`）、`STRATA_GFX906_ATTN_REDUCE12` 两条同义行 + 一条 **name 里带等号与括号**的 `STRATA_GFX906_ATTN_REDUCE12=1（attn 分块的另一种归约）`、一条 **name 是整句中文**的 `ROCm userland 10.1.0 + rocBLAS 5.7（…）`；**少** `STRATA_GFX906_TUNED` / `STRATA_DECODE_TIMING` / `STRATA_SPEC_DEPTH` / `STRATA_PREFILL_TIMING`（这四项在 register 里登记成 MEASUREMENT/POLICY scope，不是 ENV），并仍写 IQ4_XS 时代的 `tokenizer`/`model_name`。**后果**：若按铁律「register→gen_config --write→推 166」执行，会把 `STRATA_GFX906_TUNED=1`（gfx906 调优内核族的总开关）丢掉，等于静默降级全部 tuned kernel。**处置**：本轮改参走「在产 config ⊕ 声明增量」并由 D5 增量门验（`P491`）；工具链对齐另立 `R106`：① 四个观测/调优 env 的 scope 改 ENV 且值只写值；② 三条坏行改成合法键或降为 REFERENCE；③ META 的 tokenizer/model_name 按现役 pack 更正；④ 加负向自测（坏行必须报错而不是静默生成）。",
  "P491", "KW:gen_config|GFX906_TUNED|R106"),
 ("B6判定探针", "P493",
  "`elastic K/V` 这一行**不能整文件 grep**：日志 append-only，上一次窗口的旧行会让新检查假通过 ⇒ 必须按行号偏移切片",
  "W1040", "count", "1", "1", "DONE",
  "**实测**：装机后 `grep -a \"elastic K/V\" <log> | tail -2` 仍会拿到 13:44 那次窗口的行（第 148458 行），而当前进程是 14:13:52 起的（第 148765 行之后）。`P478` 写的硬门 `grep -aq \"elastic K/V:\"` 在**第二次**运行同一脚本时就会假通过 —— 门本身没问题，**取样面错了**。**修法（本轮窗口已用）**：起容器前记 `wc -l`，起来后 `tail -n +$((BEFORE+1))` 到 `new_start.log`，只在切片里判「有 elastic 行 / 无 `--kv-grow is off` / 无 `could not map`」。**推广**：所有「引擎自报状态」的门（`--kv-grow is off`、`elastic K/V`、`expert cache N slots`、`ERR …`）一律按请求/启动切片读，不按整文件 tail —— 这是 `P465`（探针先证可见性）同一族的第二半：**看不见 ≠ 没发生，看见了也可能是上一次的**。",
  "P478;P488", "KW:append-only|行号偏移|假通过"),
 ("B9显存", "P494",
  "增长到底怎么发生的（实测原文）：一次 20K token 请求只借 **19–55 槽**，且**更热的专家是换到冷专家的槽里、不是被赶走** ⇒ 20000 token 的 logits 仍逐位不变",
  "W1040", "count", "1", "1", "DONE",
  "**数值臂原文（`tmp/w1040/pa_B/stderr.txt`）**：`strata: K/V grown to 20512 cells (0.26 GiB); the expert cache gave 19 slots for it, 15 hotter experts moved to colder ones' slots (1896 of 1915 slots hold experts)`；生产 28.7K 请求上是 `grown to 24576` / `32768 cells`，`gave 25–55 slots`，`8246–8273 of 8301 slots hold experts`。**机制（源码 `generate.cpp` kvg_ensure 注释逐字）**：让出的槽是「prompt path loan 正下方」那些中等热度的，一个比 loan 区最冷者更热的专家会被**搬到它那个槽**（device copy），最冷的才真正让出 ⇒ **驻留集合近似不变，只有槽号变**；加之外层 `step=8192` 让增长按整步走、`floor=128` 保证缓存至少留 128 槽。**⇒ 这就是「增长了 4128 个 cell、logits 却逐位相同」的解释**（`P495`）：被真正赶出缓存的那 4 个专家，这段文本没有路由到。**代价面的真实尺寸**：20K 上下文 ⇒ 19–55 槽（0.2–0.7% 的缓存），不是「把专家池吃掉」。",
  "P490;P495", "KW:24576|换到|逐位"),
 ("B2数值债", "P495",
  "装机数值证据：**1000 / 8000 / 16000 / 20000 token 四个 prompt 的 fp32 全词表 logits 逐字节相同**（含强制一次增长的 20000）；28,695 token 的 needle 前后都命中",
  "W1040", "count", "1", "1", "DONE",
  "**做法（`tmp/w1040/qq_prompt.py`，把 yardstick 的 `PROMPT_LENS` 扩到 `(1000,8000,16000,20000)`）**：两臂 = `b12180` 与 `kvg`+`--kv-grow`，其余完全同参（`--expert-cache 1500` ⇒ 实得 1915 槽、`--kv k8v4`、`--max-context 20512`），dump 是 `STRATA_DUMP_FIRST_LOGITS` 的 float32 全词表（993,280 B/个）。**结果**：`cmp -s` 四个文件全 identical（md5 `54d98428…`/`131abb31…`/`31b4a2d7…`/第四份亦同），`pcompare` = `prompts 4 top-1 100.00% KL mean 0.00000 max 0.00000`。**关键**：`first.3`（20000 token）**也在其中**，而该臂 stderr 明确打出 `K/V grown to 20512 cells … gave 19 slots`（`P494`）⇒ **增长路径被执行过，位仍没动**，这就把「弹性映射会不会算错地址」这一层结掉了。**1000–16000 三点本来就不可能增长**（`STRATA_KV_GROW_INIT=16384`），它们是「无增长时是否位相同」的对照。**功能面**：28,695 token 的 needle（码埋在开头，1.8 万词填充，贪心）安装前 `hit=True`（38.6 s）、安装后 `hit=True`（39.0 s），两臂 `cached_tokens=0` 排除提示缓存复用。**仍缺**：长上下文 *decode* 侧的位一致（本次只测 prompt 路径的 next-token logits）。",
  "P490;P494", "KW:逐字节|pcompare|needle"),
]

P = io.open(PROG, encoding="utf-8").read()
assert len(ROWS[0]) == 11 and all("\t" not in x for x in ROWS[0])
shutil.copy2(PROG, PROG + ".bak_w1040_" + time.strftime("%Y%m%d_%H%M%S"))
lines = P.splitlines()
hi = next(i for i, l in enumerate(lines) if l.split("\t")[0] == "block")
hdr = lines[hi].split("\t")
assert hdr[0] == "block" and len(hdr) in (10, 11), hdr
have = {l.split("\t")[1] for l in lines if l.count("\t") >= 1 and not l.startswith("#") and l.split("\t")[0] != "block"}
for r in ROWS:
    assert r[1] not in have, r[1]
    assert len(r) == 11 and "\t" not in "".join(r), r[1]
out = []
upd = {"P444": ("1", "DONE", "（W1040 收口：R104 已装机，`P490`）"),
       "P474": ("1", "DONE", "（W1040：候选已装机，见 `P490`）"),
       "P488": ("1", "DONE", "（W1040：窗口结论已落生产，见 `P490`）")}
hit = 0
for ln in lines:
    f = ln.split("\t")
    if len(f) >= 10 and f[1] in upd and not ln.startswith("#"):
        d, st, add = upd[f[1]]
        f[6], f[7] = d, st
        f[8] = f[8] + add
        hit += 1
        ln = "\t".join(f)
    out.append(ln)
assert hit == 3, hit
out += ["\t".join(r) for r in ROWS]
io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")

# ---------------------------------------------------------------- totals
tot = done = 0
for l in io.open(PROG, encoding="utf-8"):
    f = l.rstrip("\n").split("\t")
    if len(f) >= 10 and f[0] not in ("block",) and not l.startswith("#"):
        try:
            tot += int(f[5]); done += int(f[6])
        except ValueError:
            pass
pct = 100.0 * done / tot
print("PROGRESS: %d 条 / 已结 %d (%.1f%%)" % (tot, done, pct))
io.open(os.path.join(ROOT, "albus", "w1040", "totals.txt"), "w", encoding="utf-8").write(
    "%d %d %.1f\n" % (tot, done, pct))
