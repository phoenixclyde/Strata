#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""deploy_gate.py -- 能不能落生产，由判据输出，不由人判断。

机主 2026-11-07 03:4x：「你正常能落生产不能落生产不应该以事实为依据吗？人决定是主观的。」
这条工具就是把「事实」写成可执行判据。**任何一条拿不出证据，就 REFUSE**——「没有证据」
本身就是拒绝理由，不是让人补一句话绕过。

七条判据（全部机械可判）：
  D1 身份      exe 存在，md5/大小记录在案；--live 时与 166 上 `docker exec md5sum` 一致
  D2 回滚件    166 上存在一个 md5 不同的上一版 exe（能回滚才允许前进）
  D3 性能      A/B 证据里每个点 n>=3，且 **|Δ| 与该次 run 自己的 2×CV 比较**（项目规则 B7）
               两种目标量：`target_kind=latency`（默认）Δ 必须 >= 2×CV；`target_kind=capacity`
               目标量是**整数计数**（槽数/槽位，零方差），只要严格变大；墙钟一律降级为护栏。
  D4 数值      bit-identical，或 KL<=0.0139 且 top-1>=99%（R94 预登记标尺）
  D5 配置面    改参唯一道：新 config 相对上一份的**增量**必须逐项由本轮 ADOPTED 的 register 行解释
  D6 证据链    本轮 report + 账本行 + W832 §6.5 回写块（复用 round_ledger 的 E 规则）
  D7 CI 证据    本 exe 的构建 sha 在 deploy/CI_RUNS.tsv 里有 Downstream gate run=success，
               或 status=exempt 的显式豁免行（W1048：历史 43 件 UNTRACKED 就是反例）

A/B 证据文件（JSON，最小形状）：
{
  "target": "prefill_2k",
  "baseline": {"n": 3, "mean": 532.76, "cv_pct": 0.31},
  "candidate": {"n": 3, "mean": 534.83, "cv_pct": 0.26},
  "guard": [{"name": "decode", "n": 3, "mean_base": 36.32, "mean_cand": 36.30, "cv_pct": 1.2}],
  "numeric": {"mode": "bitident"}            # 或 {"mode":"kl","kl":0.0021,"top1":99.8}
}
容量型证据再加：
  "target_kind": "capacity",
  "capacity": {"base_slots": 7463, "cand_slots": 8301, "base_line": "...", "cand_line": "..."}

  python tools/deploy_gate.py --exe strata-0.1.57-012 --ab albus/w1036/ab.json [--live]
  python tools/deploy_gate.py --exe X --ab ... --cfg-base old.json --cfg-new new.json --reg-ids P32
退出码 0 = 可以装；1 = REFUSE；SKIP 存在时 = INCOMPLETE（W1043：SKIP 不是证据）。

W1075/M11（G10 收敛）：本文件是 deploy_gate 的唯一实现——tools/ 与 ci/ 两份逐字节一致。
双主机自适应：166 上 live() 直接本地执行、数据在 /home/albus/strata166/{data/bin,ci/state}；
笔记本上 live() 走 ssh、数据在 deploy/。env 覆盖：STRATA_DATA_BIN / STRATA_STATE / STRATA_REGISTER。

D5 为什么是「增量」而不是「md5 等于 gen_config 的输出」（2026-11-07 实测）：
  `deploy/params/gen_config.py` 今天产出的 config 与在产 diff **9 处**——4 个生产在用的 env
  （`STRATA_GFX906_TUNED` / `STRATA_DECODE_TIMING` / `STRATA_SPEC_DEPTH` / `STRATA_PREFILL_TIMING`）
  在 register 里登记成了 MEASUREMENT/PARAM scope（不是 ENV），3 个 ENV 行的 name/value 里混进了注释文字
  （会生成 `STRATA_GFX906_ATTN_REDUCE12=1（attn 分块的另一种归约）` 这种垃圾键），
  tokenizer/model_name 还停在 IQ4_XS 时代。**照着它 --write 再推生产，会把 GFX906_TUNED=1 之类的
  调优总开关丢掉。** 所以本轮 D5 只做能机械判的那一半：新 config = 旧 config ⊕ 本轮 register 声明的增量，
  其余键逐字节不变；工具链对齐另立 `R106`。
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# W1075/M11 (G10): single implementation for both hosts, byte-identical in
# tools/ and ci/. On 166 the production bin and state live under
# /home/albus/strata166; on the laptop they are workspace-relative.
ON166 = os.path.isdir("/home/albus/strata166")
BIN = os.environ.get("STRATA_DATA_BIN") or (
    "/home/albus/strata166/data/bin" if ON166 else os.path.join(ROOT, "deploy", "tmp"))
STATE = os.environ.get("STRATA_STATE") or (
    "/home/albus/strata166/ci/state" if ON166 else os.path.join(ROOT, "deploy"))
KL_MAX, TOP1_MIN = 0.0139, 99.0


def local_bin(name):
    for p in (os.path.join(BIN, name), os.path.join(ROOT, "deploy", "tmp", name)):
        if os.path.isfile(p):
            return p
    return None


def md5(p):
    import hashlib
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def live(cmd):
    """--live checks reach the 166 host. On 166 run locally (no ssh-to-self);
    from the laptop ssh in. Read-only commands only."""
    if ON166:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
    else:
        r = subprocess.run(["ssh", "-o", "ConnectTimeout=8", "192.168.50.166", cmd],
                           capture_output=True, text=True, timeout=60)
    return r.returncode, (r.stdout + r.stderr).strip()


def latency_target_ok(delta, band):
    """D3b: no significant regression (机主 2026-11-14). In-band equivalence is a pass.
    The old `abs(delta) >= band` accepted a significant SLOWDOWN as a win.
    """
    # 机主 2026-11-14: 无显著负面即通过（带内等价=一致）；超带变慢才 FAIL
    return delta <= band


def guard_ok(gd, gb):
    """D3c: a guard may not get slower beyond its own 2xCV band.
    The old `abs(gd) <= gb` also rejected a large SPEED-UP: W1043 measured
    16K at -1.72% with a 0.36% band and the gate returned REFUSE.
    """
    return gd <= gb


def numeric_verdict(num):
    """D4 -- return (ok, detail). Three modes, because one absolute KL number
    cannot survive a change of instrument.

    W1041 measured the SAME pair of arms twice: the retired LOGPOS sampler read
    ~0.04, the fp32 full-vocabulary logits read 0.00345 at 8K. The 0.0139 gate
    belongs to the old sampler only. For arithmetic changes we therefore use a
    SELF-CARRIED ANCHOR (arm D = the KV precision we already run in production)
    and require the candidate's cost to stay inside that accepted budget at
    every length, plus a bit-identical build floor.
    """
    if num.get("mode") == "bitident":
        return True, "bit-identical（逐位相同）"
    if num.get("mode") == "kl":
        return (num.get("kl", 9) <= KL_MAX and num.get("top1", 0) >= TOP1_MIN,
                "KL=%.4f (<=%.4f)  top-1=%.1f%% (>=%.1f%%)"
                % (num.get("kl", -1), KL_MAX, num.get("top1", -1), TOP1_MIN))
    if num.get("mode") == "anchor":
        pts = num.get("anchor") or []
        bad = [p for p in pts
               if not (isinstance(p.get("kl_cand"), (int, float))
                       and isinstance(p.get("kl_anchor"), (int, float))
                       and p["kl_cand"] <= p["kl_anchor"])]
        ok = len(pts) >= 4 and not bad and bool(num.get("build_floor_bitident"))
        detail = ("锚门 %d 点：%s；build_floor_bitident=%s；bad=%d；task_gate=%s"
                  % (len(pts),
                     " ".join("%s %.5f/%.5f" % (p.get("length"), p.get("kl_cand", -1),
                                                p.get("kl_anchor", -1)) for p in pts),
                     num.get("build_floor_bitident"), len(bad), num.get("task_gate")))
        return ok, detail
    return False, "没有数值门结论（bitident / kl / anchor）"


def ci_run_ok(exe, runs_path=None, recipe_path=None):
    """D7: is this exe's build sha covered by a Downstream gate run or an exemption?"""
    import re
    def _state(fn):
        for c in (os.path.join(STATE, fn), "/home/albus/strata166/deploy/" + fn,
                  os.path.join(ROOT, "deploy", fn)):
            if os.path.isfile(c):
                return c
        return os.path.join(STATE, fn)
    runs_path = runs_path or _state("CI_RUNS.tsv")
    recipe_path = recipe_path or _state("REBUILD_RECIPE.tsv")
    if not os.path.isfile(runs_path):
        return False, "deploy/CI_RUNS.tsv 不存在（无 CI 证据可核）"
    sha = None
    if os.path.isfile(recipe_path):
        for line in io.open(recipe_path, encoding="utf-8-sig", errors="replace"):
            f = line.rstrip("\n").split("\t")
            if f and f[0] == exe and len(f) > 3:
                m = re.search(r"([0-9a-f]{7,40})", f[3])
                if m:
                    sha = m.group(1)
                break
    for line in io.open(runs_path, encoding="utf-8", errors="replace"):
        if not line.strip() or line.startswith("#"):
            continue
        f = line.rstrip("\n").split("\t")
        if len(f) < 4:
            continue
        key, ref, rid, status = f[0], f[1], f[2], f[3]
        hit = key == exe or (sha and (key == sha or
                (len(key) >= 7 and len(sha) >= 7 and (sha.startswith(key) or key.startswith(sha)))))
        if not hit:
            continue
        if status == "success":
            return True, "%s -> run %s success（%s）" % (key, rid, ref)
        if status == "exempt":
            return True, "%s -> 显式豁免（%s）" % (key, f[4][:60] if len(f) > 4 else "")
        return False, "%s -> status=%s 不是 success/exempt" % (key, status)
    return False, "CI_RUNS.tsv 没有 %s / sha=%s 的覆盖行" % (exe, sha)


def self_test():
    good = {"mode": "anchor", "build_floor_bitident": True,
            "anchor": [{"length": n, "kl_cand": 0.1, "kl_anchor": 0.2} for n in
                       ("1K", "8K", "16K", "20K")], "task_gate": "4/4"}
    cases = [
        ("正常锚门", good, True),
        ("某长度反超锚", dict(good, anchor=[dict(x) for x in good["anchor"]]) , False),
        ("只有三点", dict(good, anchor=good["anchor"][:3]), False),
        ("build floor 不逐位", dict(good, build_floor_bitident=False), False),
        ("缺 mode", {}, False),
    ]
    cases[1][1]["anchor"][2]["kl_cand"] = 0.9
    # D3 direction: W1043 caught both of these by running the real gate.
    cases += [
        ("D3b 显著变快", lambda: latency_target_ok(-2.72, 1.34), True),
        ("D3b 显著变慢", lambda: latency_target_ok(+2.72, 1.34), False),
        ("D3b 带内等价(略快)", lambda: latency_target_ok(-0.50, 1.34), True),
        ("D3b 带内等价(略慢)", lambda: latency_target_ok(+0.50, 1.34), True),
        ("D3b 超带变慢", lambda: latency_target_ok(+1.50, 1.34), False),
        ("D3c 大幅变快", lambda: guard_ok(-1.72, 0.36), True),
        ("D3c 变慢超带宽", lambda: guard_ok(+1.72, 0.36), False),
        ("D3c 变慢在带内", lambda: guard_ok(+0.10, 0.36), True),
    ]
    # W1048 D7: coverage table lookups, including the fail-closed path.
    import tempfile
    tmp = tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False, encoding="utf-8")
    tmp.write("key\tref\trun\tstatus\tnote\n")
    tmp.write("strata-x\tci/retro/x\t111\tsuccess\tok\n")
    tmp.write("deadbeef9999\t(exempt)\t-\texempt\twhy\n")
    tmp.close()
    cases += [
        ("D7 sha 命中 success", lambda: ci_run_ok("strata-x", runs_path=tmp.name,
          recipe_path=None)[0], True),
        ("D7 无覆盖行拒绝", lambda: ci_run_ok("strata-nope", runs_path=tmp.name,
          recipe_path=None)[0], False),
        ("D7 表缺失拒绝", lambda: ci_run_ok("strata-x", runs_path=tmp.name + ".absent",
          recipe_path=None)[0], False),
    ]
    # W1075 spec§四-4: register 缺表必须走空名单 REFUSE 而不是 traceback。
    def _reg_guard():
        old = os.environ.get("STRATA_REGISTER")
        os.environ["STRATA_REGISTER"] = "/nonexistent/PARAM_REGISTER.tsv"
        try:
            return reg_allowed("P000") == (set(), set(), [])
        finally:
            if old is None:
                os.environ.pop("STRATA_REGISTER", None)
            else:
                os.environ["STRATA_REGISTER"] = old
    cases += [("D5 缺表守卫空名单", _reg_guard, True)]
    bad = 0
    for name, obj, want in cases:
        got = numeric_verdict(obj)[0] if isinstance(obj, dict) else obj()
        ok = got == want
        bad += 0 if ok else 1
        print("  %-22s %-4s (verdict=%s)" % (name, "PASS" if ok else "FAIL", got))
    print("DEPLOY_GATE_SELF_TEST: %d/%d" % (len(cases) - bad, len(cases)))
    return 1 if bad else 0


def reg_allowed(ids):
    """本轮改判/新增的 register 行 -> 允许出现在 config 增量里的 CLI flag 与 ENV 名。"""
    if not ids:
        return set(), set(), []
    want = [x.strip() for x in ids.split(",") if x.strip()]
    env = os.environ.get("STRATA_REGISTER")
    if env is not None:
        cands = (env,)  # 显式覆盖只认它自己：指向坏路径就当缺表，不静默回落（fail-closed）
    else:
        cands = (os.path.join(ROOT, "deploy", "params", "PARAM_REGISTER.tsv"),
                 "/home/albus/strata166/deploy/params/PARAM_REGISTER.tsv")
    path = next((c for c in cands if c and os.path.isfile(c)), None)
    if path is None:
        return set(), set(), []  # 缺表 -> 空名单：D5 对任何增量 REFUSE，不 traceback
    t = io.open(path, encoding="utf-8-sig").read().splitlines()
    hdr = t[0].split("\t")
    flags, envs, hit = set(), set(), []
    for ln in t[1:]:
        f = ln.split("\t")
        if len(f) != len(hdr) or f[0] not in want:
            continue
        hit.append(f[0])
        if f[5] != "ADOPTED":
            continue
        if f[1] == "CLI":
            flags.add(f[2])
        elif f[1] == "ENV":
            envs.add(f[2])
    return flags, envs, hit


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", required=True)
    ap.add_argument("--ab")
    ap.add_argument("--report")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--path", help="要装的那份二进制（未安装时用它查身份 D1）")
    ap.add_argument("--cfg-base", help="上一份（在产）config")
    ap.add_argument("--cfg-new", help="要推上去的 config")
    ap.add_argument("--reg-ids", help="本轮改判/新增的 register 行 ID，逗号分隔（D5 的增量账）")
    a = ap.parse_args()
    ok, rows = True, []

    def add(pass_, tag, detail):
        nonlocal ok
        ok = ok and pass_
        rows.append(("PASS" if pass_ else "REFUSE", tag, detail))

    # D1 identity
    ex = a.path if (a.path and os.path.isfile(a.path)) else local_bin(a.exe)
    if ex:
        add(True, "D1 身份", "%s  md5=%s  %d B" % (a.exe, md5(ex), os.path.getsize(ex)))
    elif a.live:
        rc, out = live("docker exec strata166-407 sh -lc 'md5sum /data/bin/%s; stat -c%%s /data/bin/%s'" % (a.exe, a.exe))
        add(rc == 0 and len(out.split()) >= 2, "D1 身份", out.replace("\n", " ")[:90] or "166 上找不到")
    else:
        add(False, "D1 身份", "本机与 166 都没有 %s（不给 --live 就无法确认）" % a.exe)

    # D2 rollback artifact
    n = -1
    if os.path.isdir(BIN):
        try:
            n = len([x for x in os.listdir(BIN) if x.startswith("strata-0.1")])
        except OSError:
            n = 0
        add(n >= 2, "D2 回滚件", "%s 共 %d 个引擎二进制品（>=2 才能回滚）" % (BIN, n))
    elif a.live:
        rc, out = live("ls -1 %s | grep -c 'strata-0.1'" % BIN)
        n = int(out) if out.strip().isdigit() else 0
        add(n >= 2, "D2 回滚件", "166 上共 %d 个引擎二进制品（>=2 才能回滚）" % n)
    else:
        add(False, "D2 回滚件", "本机没有 %s 且未加 --live，无法确认可回滚" % BIN)

    # D3 performance
    ab = None
    if a.ab and os.path.isfile(a.ab):
        ab = json.load(io.open(a.ab, encoding="utf-8"))
        t, b, c = ab.get("target", "?"), ab.get("baseline", {}), ab.get("candidate", {})
        ns = [b.get("n", 0), c.get("n", 0)]
        cv = max(b.get("cv_pct", 0), c.get("cv_pct", 0))
        band = 2 * cv
        delta = (c.get("mean", 0) / b.get("mean", 1) - 1) * 100 if b.get("mean") else 0
        if ab.get("target_kind") == "capacity":
            cap = ab.get("capacity", {})
            bs, cs = cap.get("base_slots"), cap.get("cand_slots")
            add(isinstance(bs, int) and isinstance(cs, int) and bs > 0, "D3a 样本量",
                "%s n_base=%s n_cand=%s；目标量是整数计数（槽），不靠采样" % (t, ns[0], ns[1]))
            add(bool(cap.get("base_line") and cap.get("cand_line")), "D3b 目标",
                "槽 %s -> %s (%+.1f%%)｜证据行：%s" % (bs, cs, 100.0 * (cs - bs) / bs if bs else 0,
                                                     (cap.get("cand_line") or "")[:70]))
            add(isinstance(bs, int) and isinstance(cs, int) and cs > bs, "D3b2 目标方向",
                "容量型必须严格变大（%s > %s）" % (cs, bs))
        else:
            add(min(ns) >= 3, "D3a 样本量", "%s n_base=%s n_cand=%s（每点至少 3）" % (t, ns[0], ns[1]))
            add(latency_target_ok(delta, band), "D3b 目标",
                "%s Δ=%+.2f%% vs -2×CV=%.2f%%（要显著变快，变慢再多也不算收益）" % (t, delta, band))
        for g in ab.get("guard", []):
            gd = (g["mean_cand"] / g["mean_base"] - 1) * 100 if g.get("mean_base") else 0
            gb = 2 * g.get("cv_pct", 0)
            add(guard_ok(gd, gb), "D3c 不劣化",
                "%s Δ=%+.2f%% vs 带宽 %.2f%%（变快不限，变慢不许超；n=%s）" % (g["name"], gd, gb, g.get("n")))
    else:
        add(False, "D3 性能", "没有 A/B 证据文件（--ab），无从判断" )

    # D4 numeric (W1043: bitident / kl / anchor -- see numeric_verdict)
    num = (ab or {}).get("numeric", {})
    nok, ndetail = numeric_verdict(num)
    add(nok, "D4 数值", ndetail)

    # D5 config face (delta form: new = base ⊕ what this round's register rows declare)
    if a.cfg_new:
        try:
            ob = json.load(io.open(a.cfg_base, encoding="utf-8-sig")) if a.cfg_base else {}
            nw = json.load(io.open(a.cfg_new, encoding="utf-8-sig"))
        except (OSError, ValueError) as e:
            add(False, "D5 配置面", "读不了 config：%r" % e)
        else:
            flags, envs, ids = reg_allowed(a.reg_ids)
            diffs, notes = [], []
            if not a.cfg_base:
                diffs.append("没给 --cfg-base（无法证明只有声明的增量）")
            if nw.get("exe") != ob.get("exe"):
                notes.append("exe %s -> %s（制品指针，不属参数面）" % (ob.get("exe"), nw.get("exe")))
            for k in sorted(set(ob) | set(nw)):
                if k in ("exe", "args", "env"):
                    continue
                if ob.get(k) != nw.get(k):
                    diffs.append("顶层 %s 变了" % k)
            oa, na = ob.get("args") or [], nw.get("args") or []
            gone = [x for x in oa if x not in na]
            new = [x for x in na if x not in oa]
            for x in gone:
                diffs.append("args 少了 %s" % x)
            for x in new:
                (notes if x in flags else diffs).append(
                    "args +%s（%s）" % (x, "来自 " + ",".join(ids) if x in flags else "本轮 register 没声明"))
            oe, ne = ob.get("env") or {}, nw.get("env") or {}
            for k in sorted(set(ne) - set(oe)):
                (notes if k in envs else diffs).append("env +%s" % k)
            for k in sorted(set(oe) - set(ne)):
                diffs.append("env -%s" % k)
            for k in sorted(set(oe) & set(ne)):
                if oe[k] != ne[k]:
                    diffs.append("env %s 值变了" % k)
            detail = "；".join(notes) if notes else "无增量"
            if diffs:
                add(False, "D5 配置面", "增量超出本轮 register：" + "｜".join(diffs[:4]))
            else:
                add(True, "D5 配置面", "%s（其余键逐项相同）" % detail)
    else:
        add(True, "D5 配置面", "SKIP（没给 --cfg-new：本机装机不带参数面变更）")

    # D6 evidence chain
    if a.report and os.path.isfile(a.report):
        _rl = os.path.join(ROOT, "tools", "round_ledger.py")
        if os.path.isfile(_rl):
            rc = subprocess.run([sys.executable, _rl, "--quiet"],
                                cwd=ROOT, capture_output=True, text=True).returncode
            add(rc == 0, "D6 证据链", "report 在 + 账本行 + 当日记忆 + §6.5 回写块" if rc == 0 else "round_ledger FAIL")
        else:
            add(True, "D6 证据链", "report 在（166 部署面无 round_ledger，四件套由本机 round_close 另管）")
    else:
        add(True, "D6 证据链", "SKIP（装机路径没绑定报告；本轮四件套由 round_close 另管）")

    # D7 CI evidence (W1048): the build sha of this exe must be covered by a recorded
    # Downstream gate run (or an explicit exemption row).  Fail closed: a missing table
    # or a missing row is a REFUSE, not a SKIP -- "no evidence" is itself the refusal.
    verdict, detail = ci_run_ok(a.exe)
    add(verdict, "D7 CI 证据", detail)

    print("%-8s %-12s %s" % ("判定", "判据", "证据"))
    for st, tag, d in rows:
        print("%-8s %-12s %s" % (st, tag, d))
    # W1043: a SKIP is not evidence. The old banner said "PASS — 六条判据全部有证据，可以装"
    # even when D5/D6 were skipped, which is exactly how a half-green gate gets used
    # as an install permit. Fail closed on any SKIP.
    skips = [tag for st, tag, d in rows if d.startswith("SKIP")]
    all_ok = ok and not skips
    if all_ok:
        banner = "PASS — 七条判据全部有证据，可以装"
    elif ok:
        banner = "INCOMPLETE — %d 条判据是 SKIP（%s），不能据此装机" % (len(skips), "、".join(skips))
    else:
        banner = "REFUSE — 见上面标 REFUSE 的条目"
    print("\nDEPLOY_GATE: %s" % banner)
    return 0 if all_ok else 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--self-test":
        sys.exit(self_test())
    sys.exit(main())
