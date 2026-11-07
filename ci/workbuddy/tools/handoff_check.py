#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1034 -- a new session must be able to prove it picked up the right handoff.

WorkBuddy docs (Task-Bar) say each conversation is an independent task with its
own context.  So the handoff lives in files, not in chat history.  This gate
checks the three handoff artefacts stay complete and rot-free:

  A  all authority files + handoff artefacts exist
  B  the pasteable prompt is 800..3000 chars (3000 = input-box fold threshold)
     and still carries every critical anchor
  C  the SNAPSHOT line parses and has stable identifiers
  D  the live queue is unique, and the denominator agrees with PROGRESS.tsv
  E  every gate in round_close.py HARD exists, including this one
  F  the /strata-handoff slash command and the latest round report exist
  G  the prompt hard-codes no drifting denominator / queue numbers

  python tools/handoff_check.py [--self-test] [--live]

--live additionally reads (never writes) 192.168.50.166 to compare the running
engine md5 and config md5 with SNAPSHOT.  Default is offline so it is cheap
enough to run on every round close.
"""
import io
import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROMPT = os.path.join(ROOT, "albus", "w1034", "HANDOFF_PROMPT.md")
HANDOFF = os.path.join(ROOT, "albus", "w1034", "HANDOFF.md")
PLAN = os.path.join(ROOT, "deploy", "W832_OPT_PLAN_V2.md")
PROG = os.path.join(ROOT, "deploy", "PROGRESS.tsv")
ROUND_CLOSE = os.path.join(ROOT, "albus", "w1002", "round_close.py")
COMMAND = os.path.join(ROOT, ".codebuddy", "commands", "strata-handoff.md")

AUTHORITY = [
    os.path.join(ROOT, "deploy", "W832_OPT_PLAN_V2.md"),
    os.path.join(ROOT, "deploy", "PROGRESS.tsv"),
    os.path.join(ROOT, "deploy", "params", "PARAM_REGISTER.tsv"),
    os.path.join(ROOT, "deploy", "AUDIT_INDEX.md"),
    os.path.join(ROOT, "deploy", "ID_MAP.tsv"),
    os.path.join(ROOT, "albus", "w1003", "mirror_check.py"),
    os.path.join(ROOT, "albus", "w1002", "round_close.py"),
]

ANCHORS = [
    "D:\\workbuddy_space\\strata_ws",   # workspace must be selected explicitly
    "HANDOFF.md",                      # full handoff artefact
    "handoff_check.py",                # self-proof gate
    "W832_OPT_PLAN_V2.md",             # single source of current values
    "PROGRESS.tsv",                    # single ledger
    "PARAM_REGISTER.tsv",              # single parameter register
    "mirror_check.py --sync",          # six authority files to 166
    "round_close.py",                  # round-close ritual
    "present_files",                   # never show files to the owner
    "断电冷启",                          # no systemctl reboot on 166
    "P392",                            # the still-open numerical gate
    "有技能必须用技能",                    # skills are mandatory for memory work
]

SNAP_KEYS = ("round", "date", "prod_exe", "prod_md5", "config_md5",
             "container", "image", "branch", "picks")


def read(path):
    return io.open(path, encoding="utf-8", errors="replace").read()


def denominator(prog_text, plan_text):
    tot = done = 0
    for l in prog_text.splitlines():
        f = l.split("\t")
        if len(f) >= 10 and f[0] != "block" and not l.startswith("#"):
            try:
                tot += int(f[5]); done += int(f[6])
            except ValueError:
                pass
    m = re.search(r"\| 进度分母 \| \*\*(\d+) 条 / 已结 (\d+) /", plan_text)
    return tot, done, (int(m.group(1)), int(m.group(2))) if m else None


def snapshot(handoff_text):
    m = re.search(r"^> SNAPSHOT:\s*(.+)$", handoff_text, re.M)
    if not m:
        return {}
    out = {}
    for kv in m.group(1).split():
        if "=" in kv:
            k, v = kv.split("=", 1)
            out[k] = v
    return out


def hard_gates(rc_text):
    m = re.search(r"HARD\s*=\s*\[(.*?)\]", rc_text, re.S)
    return re.findall(r'"([^"]+\.py)"', m.group(1)) if m else []


def check_texts(prompt, handoff, plan, prog, rc, cmd, files_ok, gates, latest_report):
    """Pure checks -- self-test feeds mutated texts here."""
    fails = []
    if not files_ok:
        fails.append("A: one or more authority/handoff files missing")
    n = len(prompt)
    if not 800 <= n <= 3000:
        fails.append("B: prompt is %d chars (must be 800..3000, input folds above 3000)" % n)
    missing = [a for a in ANCHORS if a not in prompt]
    if missing:
        fails.append("B: prompt lost anchors: %s" % missing[:4])
    if re.search(r"\d{3} 条 / 已结 \d+", prompt):
        fails.append("G: prompt hard-codes a drifting denominator")
    if re.search(r"队列\s*`?R\d+`?\s*→", prompt):
        fails.append("G: prompt hard-codes a drifting queue")
    snap = snapshot(handoff)
    absent = [k for k in SNAP_KEYS if not snap.get(k)]
    if absent:
        fails.append("C: SNAPSHOT missing keys %s" % absent)
    for k in ("prod_md5", "config_md5"):
        if snap.get(k) and not re.fullmatch(r"[0-9a-f]{32}", snap[k]):
            fails.append("C: SNAPSHOT %s is not a 32-hex md5" % k)
    q = [l for l in plan.splitlines() if l.startswith("| **唯一队列** |")]
    sec02 = next((i for i, l in enumerate(plan.splitlines())
                  if l.startswith("### 0.2")), 10 ** 6)
    qi = next((i for i, l in enumerate(plan.splitlines())
               if l.startswith("| **唯一队列** |")), 10 ** 6)
    if len(q) != 1 or qi > sec02:
        fails.append("D: expected exactly one §0.1 唯一队列 row, got %d" % len(q))
    tot, done, declared = denominator(prog, plan)
    if declared != (tot, done):
        fails.append("D: §0.1 denominator %s != PROGRESS.tsv %d/%d" % (declared, tot, done))
    if not gates:
        fails.append("E: round_close.py HARD list unparseable")
    elif "handoff_check.py" not in gates:
        fails.append("E: handoff_check.py not wired into round_close.py HARD")
    if any(not os.path.isfile(os.path.join(ROOT, "tools", g)) for g in gates):
        fails.append("E: a HARD gate script is missing: %s" %
                     [g for g in gates if not os.path.isfile(os.path.join(ROOT, "tools", g))][:3])
    if "description:" not in cmd or "HANDOFF_PROMPT.md" not in cmd:
        fails.append("F: slash command frontmatter/body incomplete")
    if not latest_report:
        fails.append("F: latest round report missing (albus/<SNAPSHOT round>/reply.md)")
    return fails, (n, tot, done, snap)


def live_check(snap):
    """Read-only compare against the running production box.

    W1040: this used to md5 a **hard-coded** `/data/bin/strata-0.1.57-001`, so it compared the wrong
    artifact for every round after the engine name changed -- it would have failed on a correct box and
    passed on any box that still had that file.  The path now comes from the SNAPSHOT's `prod_exe`.
    """
    if not snap:
        return ["LIVE: no SNAPSHOT to compare"]
    exe = snap.get("prod_exe") or ""
    if not exe:
        return ["LIVE: SNAPSHOT has no prod_exe"]
    script = (
        'C=strata166-407; '
        'docker exec $C md5sum /data/bin/%s | cut -d" " -f1; '
        'md5sum /home/albus/strata166/data/strata-huihui-ud-iq4_xs.json | cut -d" " -f1; '
        'curl -s -m 5 localhost:8090/health | head -c 20'
    ) % exe
    try:
        out = subprocess.check_output(
            ["ssh", "-o", "ConnectTimeout=8", "192.168.50.166", script],
            stderr=subprocess.STDOUT, timeout=60).decode("utf-8", "replace")
    except Exception as e:
        return ["LIVE: cannot reach 166 (%s)" % str(e)[:80]]
    lines = [x.strip() for x in out.splitlines() if x.strip()]
    fails = []
    if not lines or lines[0] != snap.get("prod_md5"):
        fails.append("LIVE: engine md5 != SNAPSHOT (got %s)" % (lines[0] if lines else "?"))
    if len(lines) < 2 or lines[1] != snap.get("config_md5"):
        fails.append("LIVE: config md5 != SNAPSHOT (got %s)" % (lines[1] if len(lines) > 1 else "?"))
    if not any("ok" in x for x in lines):
        fails.append("LIVE: /health not ok")
    return fails


def run(live=False, quiet=False):
    paths = AUTHORITY + [PROMPT, HANDOFF, ROUND_CLOSE, COMMAND]
    missing = [os.path.relpath(p, ROOT) for p in paths if not os.path.isfile(p)]
    prompt = read(PROMPT) if os.path.isfile(PROMPT) else ""
    handoff = read(HANDOFF) if os.path.isfile(HANDOFF) else ""
    plan = read(PLAN) if os.path.isfile(PLAN) else ""
    prog = read(PROG) if os.path.isfile(PROG) else ""
    rc = read(ROUND_CLOSE) if os.path.isfile(ROUND_CLOSE) else ""
    cmd = read(COMMAND) if os.path.isfile(COMMAND) else ""
    gates = hard_gates(rc)
    snap = snapshot(handoff)
    rep = os.path.join(ROOT, "albus", snap.get("round", ""), "reply.md") if snap else ""
    fails, (n, tot, done, snap) = check_texts(
        prompt, handoff, plan, prog, rc, cmd, not missing, gates,
        os.path.isfile(rep))
    if missing:
        fails.insert(0, "A: missing %s" % missing[:4])
    if live:
        fails += live_check(snap)
    if not quiet:
        print("HANDOFF: prompt=%dch snapshot=%s denom=%d/%d gates=%d live=%s report=%s" %
              (n, snap.get("round", "-"), tot, done, len(gates),
               "on" if live else "off", "Y" if os.path.isfile(rep) else "N"))
        if fails:
            print("HANDOFF: FAIL (%d)" % len(fails))
            for f in fails:
                print("   " + f)
        else:
            print("HANDOFF: PASS (artefacts complete, prompt pasteable, values single-sourced)")
    return fails


def self_test():
    prompt, handoff = read(PROMPT), read(HANDOFF)
    plan, prog, rc, cmd = read(PLAN), read(PROG), read(ROUND_CLOSE), read(COMMAND)
    gates = hard_gates(rc)
    snap = snapshot(handoff)
    rep = os.path.join(ROOT, "albus", snap.get("round", ""), "reply.md")
    base = dict(plan=plan, prog=prog, rc=rc, cmd=cmd, files_ok=True,
                gates=gates, latest_report=os.path.isfile(rep))
    cases = [
        ("over-long prompt", dict(prompt=prompt + "x" * 3100)),
        ("lost anchors", dict(prompt=prompt.replace("present_files", "X"))),
        # W1040: the anchor used to be one literal md5, so the case went inert the moment production
        # changed engine -- a negative test that silently stops being negative is worse than none.
        ("broken SNAPSHOT", dict(handoff=re.sub(r"prod_md5=[0-9a-f]{32}", "prod_md5=bad", handoff, count=1))),
        ("denominator drift", dict(plan=plan.replace("| 进度分母 | **%d 条" % denominator(prog, plan)[0],
                                                    "| 进度分母 | **%d 条" % (denominator(prog, plan)[0] + 1)))),
    ]
    ok = 0
    for label, mut in cases:
        kw = dict(base)
        kw.update(mut)
        kw.setdefault("prompt", prompt)
        kw.setdefault("handoff", handoff)
        fails, _ = check_texts(kw["prompt"], kw["handoff"], kw["plan"], kw["prog"],
                               kw["rc"], kw["cmd"], kw["files_ok"], kw["gates"],
                               kw["latest_report"])
        ok += 1 if fails else 0
        if not fails:
            print("SELF_TEST: negative case did not fail: " + label)
    print("SELF_TEST: %d/4" % ok)
    return 0 if ok == 4 else 1


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    sys.exit(1 if run(live="--live" in sys.argv) else 0)
