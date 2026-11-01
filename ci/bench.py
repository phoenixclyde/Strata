#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""strata-ci bench -- one experiment, recorded as data instead of a shell script.

Why this exists: every A/B we ran so far lived in a bash script and its conclusion lived
in a markdown file.  Nothing was reproducible and nothing fed back into a regression gate.
This writes one JSON per run (code version, binary, env, n samples, per-sample metrics,
median + coefficient of variation) so two runs can be compared later, on the record.

The one rule it enforces: report the noise.  A delta smaller than ~2x the CV of the same
run is not a result (measured here: phase-table hc swings +/-30%).

Usage:
  bench.py --n 12 [--tokens 128] [--label hc-probe] [--url http://127.0.0.1:8090]

Exit code 0 on success; the JSON path is printed last.
"""
import argparse
import json
import os
import statistics
import subprocess
import time
import urllib.request

CFG = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"
RUNS = "/home/albus/strata166/ci/state/runs"
PROMPT = "Count from 1 to 40, one number per line."


def sh(cmd, default=""):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True,
                              timeout=30).stdout.strip() or default
    except Exception:                                    # noqa: BLE001
        return default


def ask(url, tokens):
    body = json.dumps({
        "model": "bench",
        "messages": [{"role": "user", "content": PROMPT}],
        "max_tokens": tokens,
        "temperature": 0,
        "stream": False,
    }).encode()
    req = urllib.request.Request(url + "/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.loads(r.read())
    dt = time.perf_counter() - t0
    u = d.get("usage", {})
    comp = u.get("completion_tokens", 0)
    return dt, comp, (comp / dt if dt else 0.0)


def stats(xs):
    if not xs:
        return {}
    m = statistics.median(xs)
    sd = statistics.pstdev(xs) if len(xs) > 1 else 0.0
    return {"n": len(xs), "median": round(m, 3), "mean": round(statistics.fmean(xs), 3),
            "sd": round(sd, 3), "cv_pct": round(100 * sd / m, 2) if m else None,
            "min": round(min(xs), 3), "max": round(max(xs), 3),
            "iqr": round(statistics.quantiles(xs, n=4)[2] - statistics.quantiles(xs, n=4)[0], 3)
            if len(xs) > 3 else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--warmup", type=int, default=2,
                    help="samples to discard: the first request after an idle spell carries ~2.3 s "
                         "of GPU clock ramp + cache warmup (measured: 30.5 tok/s vs 66-70 after)")
    ap.add_argument("--tokens", type=int, default=128)
    ap.add_argument("--label", default="bench")
    ap.add_argument("--url", default="http://127.0.0.1:8090")
    a = ap.parse_args()

    cfg = json.load(open(CFG))
    run = {
        "run_id": time.strftime("%Y%m%dT%H%M%S") + "-" + a.label,
        "label": a.label,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "git_head": sh("git -C /home/albus/strata166/pr/strata-fork rev-parse HEAD"),
        "git_branch": sh("git -C /home/albus/strata166/pr/strata-fork rev-parse --abbrev-ref HEAD"),
        "git_tag": sh("git -C /home/albus/strata166/pr/strata-fork describe --exact-match --tags HEAD") or None,
        "dirty": bool(sh("git -C /home/albus/strata166/pr/strata-fork status --porcelain --untracked-files=no")),
        "exe": cfg.get("exe"),
        "exe_md5": sh("md5sum %s | cut -d' ' -f1" % cfg.get("exe", "").replace(
            "/data", "/home/albus/strata166/data")),
        "env": dict(sorted((cfg.get("env") or {}).items())),
        "cfg_md5": sh("md5sum " + CFG + " | cut -d' ' -f1"),
        "workload": {"prompt": PROMPT, "max_tokens": a.tokens, "temperature": 0},
        "samples": [],
    }

    print("run_id : %s" % run["run_id"])
    print("exe    : %s (%s)" % (run["exe"], run["exe_md5"][:12]))
    print("n      : %d x %d tokens\n" % (a.n, a.tokens))

    for i in range(a.n):
        dt, comp, tps = ask(a.url, a.tokens)
        run["samples"].append({"dt_s": round(dt, 3), "completion_tokens": comp,
                               "tok_s": round(tps, 3)})
        print("  #%02d  %6.2f s  %3d tok  %6.2f tok/s" % (i + 1, dt, comp, tps))

    run["metrics"] = {}
    warm = run["samples"][a.warmup:]
    run["warmup_discarded"] = a.warmup
    run["metrics"]["tok_s"] = stats([s["tok_s"] for s in warm])
    run["metrics"]["dt_s"] = stats([s["dt_s"] for s in warm])
    run["metrics"]["tok_s_all_including_warmup"] = stats([s["tok_s"] for s in run["samples"]])

    m = run["metrics"]["tok_s"]
    print("\n--- after discarding %d warmup sample(s) ---" % a.warmup)
    print("tok/s: median %.2f  mean %.2f  sd %.2f  CV %.2f%%  range %.2f-%.2f"
          % (m["median"], m["mean"], m["sd"], m["cv_pct"], m["min"], m["max"]))
    print("=> a change is a result only if it exceeds ~2x CV = %.1f%%"
          % (2 * m["cv_pct"]))
    w = run["metrics"]["tok_s_all_including_warmup"]
    print("(with warmup it would look like CV %.2f%% -- that is the trap)" % w["cv_pct"])

    os.makedirs(RUNS, exist_ok=True)
    p = os.path.join(RUNS, run["run_id"] + ".json")
    with open(p, "w") as f:
        json.dump(run, f, indent=2)
    print("\nwritten: %s" % p)


if __name__ == "__main__":
    main()
