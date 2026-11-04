#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cfg_apply -- the only sanctioned way to change the production config's args/env.

Why this exists: on 2026-11-05 a hand-edited config turned `env` from a dict into a list
and the server died before binding.  The static gate exists, but nothing forced it to run
before a config change, and nothing rolled back when the service did not come up.

The loop this enforces (no step is optional):

  1. build a candidate from the live config (deep copy)
  2. gate.py --config CANDIDATE   -- must exit 0, or *nothing* is written
  3. backup the live config
  4. install + restart + wait for /health loaded  -- timeout => restore + restart + exit 2
  5. measure: decode tok/s (bench.py) and TTFT at 2K (built-in probe), n samples, median+CV
  6. compare against a recorded baseline: a drop bigger than 2x the pooled CV => rollback
  7. keep + write a record + one ledger line

Usage:
  cfg_apply.py --label p4d1 --set --pool-tasks=6 --apply
  cfg_apply.py --label p4d1 --env STRATA_X=1 --baseline p4-base --n 5 --apply
  (no --apply) prints the candidate diff and the gate result, changes nothing.
"""
import argparse
import copy
import json
import os
import shutil
import statistics
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
CFG = os.environ.get("CFG", "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json")
HEALTH = "http://127.0.0.1:8090/health"
URL = "http://127.0.0.1:8090"
STATE = os.path.join(HERE, "state", "cfg")
LEDGER = os.path.join(STATE, "ledger.tsv")


def sh(cmd, timeout=600):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)


def health_ok():
    try:
        with urllib.request.urlopen(HEALTH, timeout=4) as r:
            d = json.loads(r.read())
        return d.get("status") == "ok" and d.get("loaded") is True
    except Exception:                                          # noqa: BLE001
        return False


def wait_health(timeout=300):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if health_ok():
            return True, time.time() - t0
        time.sleep(5)
    return False, time.time() - t0


def restart(wait=True):
    sh("docker restart strata166-407", timeout=120)
    return wait_health() if wait else (True, 0.0)


def ttft(n, warmup=1):
    """2K-token prompt, streaming-free wall time; the engine's read time is in its log."""
    prompt = "ttft " + "The quick brown fox jumps over the lazy dog. " * 200
    body = json.dumps({"model": "x", "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": 2, "temperature": 0.0}).encode()
    vals = []
    for i in range(n + warmup):
        t0 = time.perf_counter()
        req = urllib.request.Request(URL + "/v1/chat/completions", data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=600) as r:
            r.read()
        dt = time.perf_counter() - t0
        if i >= warmup:
            vals.append(dt)
    return vals


def stats(xs):
    m = statistics.median(xs)
    sd = statistics.pstdev(xs) if len(xs) > 1 else 0.0
    return {"n": len(xs), "median": round(m, 4), "cv_pct": round(100 * sd / m, 2) if m else None}


def gate(cfg_path):
    r = sh("python3 %s/gate.py --config %s" % (HERE, cfg_path), timeout=180)
    tail = [l for l in r.stdout.splitlines() if l.startswith("FAIL") or l.startswith("gate:")]
    return r.returncode == 0, tail


def apply_sets(cfg, sets, envs):
    a = list(cfg["args"])
    for s in sets:
        if "=" not in s:
            raise SystemExit("--set wants FLAG=VALUE, got %r" % s)
        k, v = s.split("=", 1)
        if not k.startswith("--"):
            k = "--" + k
        if k in a:
            a[a.index(k) + 1] = v
        else:
            a.extend([k, v])
    cfg["args"] = a
    env = cfg.get("env")
    if not isinstance(env, dict):
        raise SystemExit("live config env is not a dict; fix it first")
    for s in envs:
        if "=" not in s:
            raise SystemExit("--env wants KEY=VALUE, got %r" % s)
        k, v = s.split("=", 1)
        env[k] = v
    return cfg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--set", action="append", default=[], help="FLAG=VALUE (args)")
    ap.add_argument("--env", action="append", default=[], help="KEY=VALUE (env dict)")
    ap.add_argument("--baseline", default=None, help="label of a recorded run to beat")
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--record-only", action="store_true", help="measure the live config, change nothing")
    a = ap.parse_args()

    os.makedirs(STATE, exist_ok=True)
    live = json.load(open(CFG))
    cand = apply_sets(copy.deepcopy(live), a.set, a.env)

    cand_path = CFG + ".candidate"      # same dir: the gate maps /data/... against it
    json.dump(cand, open(cand_path, "w"), indent=1)

    changed = [(i, live["args"][i] if i < len(live["args"]) else None, v)
               for i, v in enumerate(cand["args"]) if i >= len(live["args"]) or live["args"][i] != v]
    env_changed = {k: (live.get("env", {}).get(k), v) for k, v in cand["env"].items()
                   if live.get("env", {}).get(k) != v}
    print("== candidate: %s" % a.label)
    print("   args deltas: %s" % (changed or "none"))
    print("   env  deltas: %s" % (env_changed or "none"))

    if a.record_only:
        print("== record-only: measuring the live config, nothing is written to it")
        bench = sh("python3 %s/bench.py --n %d --label %s-decode" % (HERE, a.n, a.label), timeout=1800)
        rec_path = bench.stdout.strip().splitlines()[-1] if bench.stdout.strip() else ""
        decode = json.load(open(rec_path))["metrics"]["tok_s"] if os.path.exists(rec_path) else None
        tt = stats(ttft(a.n))
        json.dump({"label": a.label, "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                   "args": live["args"], "env": live["env"],
                   "decode": decode, "ttft": tt, "gate": "record-only"},
                  open(os.path.join(STATE, a.label + ".json"), "w"), indent=1)
        print("   decode: %s" % decode)
        print("   ttft  : %s" % tt)
        print("   record: %s" % os.path.join(STATE, a.label + ".json"))
        return 0

    ok, tail = gate(cand_path)
    print("== gate: %s" % ("PASS" if ok else "FAIL"))
    for l in tail:
        print("   " + l)
    if not ok:
        print("ABORT: gate failed, nothing written")
        return 1
    if not a.apply:
        print("DRY RUN: nothing written (pass --apply)")
        return 0

    bak = CFG + ".bak_" + time.strftime("%H%M%S")
    shutil.copy2(CFG, bak)
    json.dump(cand, open(CFG, "w"), indent=1)
    print("== installed; restart")
    up, dt = restart()
    if not up:
        print("!! health timeout after %.0fs -> ROLLBACK" % dt)
        shutil.copy2(bak, CFG)
        up2, _ = restart()
        print("   rolled back; health=%s" % ("ok" if up2 else "STILL DOWN"))
        return 2
    print("   up in %.0fs" % dt)

    print("== measure (decode n=%d, ttft n=%d)" % (a.n, a.n))
    bench = sh("python3 %s/bench.py --n %d --label %s-decode" % (HERE, a.n, a.label), timeout=1800)
    rec_path = bench.stdout.strip().splitlines()[-1] if bench.stdout.strip() else ""
    decode = None
    if os.path.exists(rec_path):
        decode = json.load(open(rec_path))["metrics"]["tok_s"]
    tt = stats(ttft(a.n))

    rec = {"label": a.label, "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "args": cand["args"], "env": cand["env"], "deltas_args": changed, "deltas_env": env_changed,
           "decode": decode, "ttft": tt, "gate": "PASS"}
    json.dump(rec, open(os.path.join(STATE, a.label + ".json"), "w"), indent=1)
    print("   decode: %s" % decode)
    print("   ttft  : %s" % tt)

    verdict, why = "KEEP", "no baseline"
    if a.baseline:
        b = json.load(open(os.path.join(STATE, a.baseline + ".json")))
        if b.get("decode") and decode:
            cv = max(b["decode"]["cv_pct"] or 0, decode["cv_pct"] or 0)
            lim = 2 * cv
            dd = 100.0 * (decode["median"] - b["decode"]["median"]) / b["decode"]["median"]
            dt2 = 100.0 * (tt["median"] - b["ttft"]["median"]) / b["ttft"]["median"]
            print("   vs %s: decode %+.2f%% (band %.2f%%), ttft %+.2f%% (band %.2f%%)"
                  % (a.baseline, dd, lim, dt2, 2 * b["ttft"]["cv_pct"]))
            if dd < -lim or dt2 > 2 * b["ttft"]["cv_pct"]:
                verdict, why = "ROLLBACK", "regression beyond 2x CV"
    print("== verdict: %s (%s)" % (verdict, why))

    if verdict == "ROLLBACK":
        shutil.copy2(bak, CFG)
        up2, _ = restart()
        print("   rolled back; health=%s" % ("ok" if up2 else "STILL DOWN"))
        return 3

    with open(LEDGER, "a") as f:
        f.write("%s\t%s\tKEEP\tdecode=%s\tttft=%s\t%s\n"
                % (rec["ts"], a.label, decode and decode["median"], tt["median"], a.set + a.env))
    print("   ledger: %s" % LEDGER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
