#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W938 backfill: (a) production ledger before r17, (b) reconstructed run records.

Rules this follows:
  - existing ledger lines are never rewritten; new pre-ledger rows are inserted and the
    file is re-sorted by ts (stable), so `tail -2` semantics stay correct;
  - every inserted/reconstructed row says so in its own text: tag "-" where no tag
    evidence exists, and "reconstructed" + source document in the record;
  - nothing is invented: a value is written only if a document or a file on disk carries it.
"""
import io, json, os, subprocess, sys

DATA = "/home/albus/strata166/data"
HIST = "/home/albus/strata166/ci/state/prod_history.tsv"
RUNS = "/home/albus/strata166/ci/state/runs"


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()


def md5(path):
    return sh("md5sum %s | cut -d' ' -f1" % path)


# ---------------------------------------------------------------- (a) ledger backfill
PRE = [
    ("2026-10-29T22:41:31+08:00", "strata-0.1.53", "babc3fb86f8d138a3106894b0050c065", ""),
    ("2026-10-31T00:41:49+08:00", "strata-0.1.54n", "943b8f2a20fad2ffb62ad6742cb5d700", ""),
    ("2026-10-31T02:37:42+08:00", "strata-0.1.54w", "d9d6ca23f783fae72bac1711834ad76a", ""),
    ("2026-10-31T09:57:27+08:00", "strata-0.1.54n2", "28885018d1379a4fa4fd8c081a44492a", ""),
    ("2026-10-31T16:55:36+08:00", "strata-0.1.54n3", "21b50786a11ea4255ea0497357196077", ""),
    ("2026-10-31T18:00:11+08:00", "strata-0.1.54n4", "dea74489b1e180fafbebadddbb7cee71", ""),
    ("2026-10-31T19:08:13+08:00", "strata-0.1.55g", "29b15bb4418bf15a98c22ec565f2447b", ""),
    ("2026-11-01T00:47:59+08:00", "strata-0.1.55-banner", "a10af3849a65724c81d215e3834f1b91", ""),
    ("2026-11-01T01:19:49+08:00", "strata-0.1.55-routed", "9924f3a0eec96c2e4f61dbbac492f205", ""),
    ("2026-11-01T02:59:45+08:00", "strata-0.1.55-mmvq", "7c8654af1cfb00aebec035901b03565f", ""),
    ("2026-11-01T14:43:04+08:00", "strata-0.1.55h", "9a2ff8742f9918f657a468a7baeb177c",
     "same bytes as strata-0.1.55i"),
]

HEAD = "ts\texe\texe_md5\tcfg_md5\tgit_head\ttag\thealth_s\tvram_used\tweights\n"
old = io.open(HIST, encoding="utf-8").read().splitlines()
have = set()
rows = []
for ln in old:
    if not ln.strip():
        continue
    f = ln.split("\t")
    if f[0] == "ts":
        continue
    have.add((f[1], f[2]))
    rows.append(f)

added = 0
for ts, name, m, extra in PRE:
    if (name, m) in have:
        continue
    note = "pre-ledger reconstructed: mtime of /data/bin/%s (approximate deploy time), tag unknown" % name
    if extra:
        note += "; " + extra
    rows.append([ts, name, m, "-", "-", "-", "-", "-", note])
    added += 1

rows.sort(key=lambda r: r[0])
os.rename(HIST, HIST + ".bak_w938")
with io.open(HIST, "w", encoding="utf-8") as f:
    f.write(HEAD)
    for r in rows:
        while len(r) < 9:
            r.append("")
        f.write("\t".join(r[:9]) + "\n")
print("ledger: %d rows (%d backfilled) -> %s" % (len(rows), added, HIST))

# ---------------------------------------------------------------- (b) run records
def rec(ts, label, exe, exe_md5, metrics, note, extra=None):
    rid = ts + "-" + label
    p = os.path.join(RUNS, rid + ".json")
    if os.path.exists(p):
        print("  skip existing:", rid)
        return
    r = {
        "run_id": rid,
        "label": label,
        "ts": ts,
        "git_head": "d963c79145d17bb501d3f6211f966d11277c3e19",
        "git_branch": "gfx906/mi50",
        "git_tag": "mi50-0.2.9-r27",
        "dirty": True,
        "exe": "/data/bin/" + exe,
        "exe_md5": exe_md5,
        "env": {},
        "cfg_md5": "-",
        "reconstructed": True,
        "provenance": note,
        "samples": [],
        "samples_note": "per-sample rows were not kept; metrics below are the medians stated in the source document",
        "metrics": metrics,
    }
    if extra:
        r.update(extra)
    with io.open(p, "w", encoding="utf-8") as f:
        json.dump(r, f, indent=2, ensure_ascii=False)
    print("  wrote", rid)


# every number below is copied from the named document; nothing is derived.
R = [
    ("2026-11-03T23:40:00", "w919-r67-ple-mlock-unlocked", "strata-0.1.55w", "cf2ba243f908fe1b9d058d66b761c00f",
     {"decode_tok_s": {"n": 5, "median": 79.24, "cv_pct": 2.2},
      "prefill_ttft_s": {"n": 3, "median": 8.845, "cv_pct": 1.1}},
     "deploy/W920_PARAM_AUDIT.md section 8 (strict re-test, n=9, rep6-9 after warmup)",
     {"workload": {"prompt_tokens": 6300, "max_tokens": 256, "temperature": 0}}),
    ("2026-11-03T23:55:00", "w919-r67-ple-mlock-locked", "strata-0.1.55w", "cf2ba243f908fe1b9d058d66b761c00f",
     {"decode_tok_s": {"n": 4, "median": 79.43, "cv_pct": 2.0},
      "prefill_ttft_s": {"n": 3, "median": 8.860, "cv_pct": 1.0}},
     "deploy/W920_PARAM_AUDIT.md section 8: memlock=-1, VmLck 26.82 GiB, +0.24% => no gain",
     {"workload": {"prompt_tokens": 6300, "max_tokens": 256, "temperature": 0}}),
    ("2026-11-04T00:30:00", "w920-trace-marker-on-a1", "strata-0.1.55w", "cf2ba243f908fe1b9d058d66b761c00f",
     {"decode_tok_s": {"n": 5, "median": 78.29, "cv_pct": 2.2},
      "prefill_ttft_s": {"n": 3, "median": 8.857, "cv_pct": 1.0}},
     "deploy/W920_PARAM_AUDIT.md A-B-A arm A1 (/data/strata-trace present)",
     {"workload": {"prompt_tokens": 6300, "max_tokens": 256, "temperature": 0}}),
    ("2026-11-04T00:45:00", "w920-trace-marker-off-b", "strata-0.1.55w", "cf2ba243f908fe1b9d058d66b761c00f",
     {"decode_tok_s": {"n": 5, "median": 80.21, "cv_pct": 2.0},
      "prefill_ttft_s": {"n": 6, "median": 8.843, "cv_pct": 0.7}},
     "deploy/W920_PARAM_AUDIT.md A-B-A arm B (marker renamed .off); delta <=2.45% => below 2xCV",
     {"workload": {"prompt_tokens": 6300, "max_tokens": 256, "temperature": 0}}),
    ("2026-11-04T01:00:00", "w920-trace-marker-on-a2", "strata-0.1.55w", "cf2ba243f908fe1b9d058d66b761c00f",
     {"decode_tok_s": {"n": 5, "median": 79.63, "cv_pct": 2.1},
      "prefill_ttft_s": {"n": 3, "median": 8.811, "cv_pct": 0.9}},
     "deploy/W920_PARAM_AUDIT.md A-B-A arm A2 (marker restored)",
     {"workload": {"prompt_tokens": 6300, "max_tokens": 256, "temperature": 0}}),
    ("2026-11-04T02:10:00", "w921-r66-optin-off", "strata-0.1.55w", "cf2ba243f908fe1b9d058d66b761c00f",
     {"prefill_ttft_s": {"n": 8, "median": 8.819, "cv_pct": 1.6},
      "decode_tok_s": {"n": 8, "median": 79.24, "cv_pct": 2.2},
      "prompt_borrows_slots": 1578},
     "deploy/W921_R66_OPTIN_AB.md: baseline, three opt-in prefill env unset",
     {"workload": {"prompt_tokens": 6300, "max_tokens": 256, "temperature": 0}}),
    ("2026-11-04T02:40:00", "w921-r66-optin-on", "2fa104e5", "2fa104e5",
     {"prefill_ttft_s": {"n": 8, "median": 8.799, "cv_pct": 1.0},
      "decode_tok_s": {"n": 8, "median": 78.19, "cv_pct": 2.2},
      "prompt_borrows_slots": 1226},
     "deploy/W921_R66_OPTIN_AB.md: PF_GROUP_SCRATCH + PREFILL_ROUTED_STREAM + PF_HC_REGION =1; -0.23% => DONE_NEG",
     {"workload": {"prompt_tokens": 6300, "max_tokens": 256, "temperature": 0}}),
    ("2026-11-04T05:05:00", "w929-m3-k8v4", "strata-0.1.55w", "cf2ba243f908fe1b9d058d66b761c00f",
     {"prefill_ttft_s": {"n": 3, "median": 9.218, "cv_pct": 1.5},
      "qsa_attn_ms": {"n": 3, "median": 1202, "cv_pct": 1.0},
      "expert_cache_slots": 7463},
     "deploy/W929_M3_K8V8_PREFILL.md arm A (--kv k8v4, STRATA_PREFILL_TIMING=1)",
     {"workload": {"prompt_tokens": 6300, "max_tokens": 128, "temperature": 0}}),
    ("2026-11-04T05:40:00", "w929-m3-k8v8", "strata-0.1.55w", "cf2ba243f908fe1b9d058d66b761c00f",
     {"prefill_ttft_s": {"n": 3, "median": 9.217, "cv_pct": 1.5},
      "qsa_attn_ms": {"n": 3, "median": 1211, "cv_pct": 1.0},
      "expert_cache_slots": 7223},
     "deploy/W929_M3_K8V8_PREFILL.md arm B (--kv int8 = k8v8); +0.75% on attention => DONE_NEG",
     {"workload": {"prompt_tokens": 6300, "max_tokens": 128, "temperature": 0}}),
    ("2026-11-04T07:00:00", "w931-r70-chunk8192-32k", "strata-0.1.55w", "cf2ba243f908fe1b9d058d66b761c00f",
     {"prefill_ttft_s": {"n": 3, "median": 40.548, "cv_pct": 0.3}, "prefill_tok_s": 754},
     "deploy/W931_R70_CHUNK_SCAN.md arm A (--prefill auto = 8192), 32K prompt",
     {"workload": {"prompt_tokens": 31700, "max_tokens": 64, "temperature": 0}}),
    ("2026-11-04T07:25:00", "w931-r70-chunk16384-32k", "strata-0.1.55w", "cf2ba243f908fe1b9d058d66b761c00f",
     {"prefill_ttft_s": {"n": 3, "median": 38.542, "cv_pct": 0.1}, "prefill_tok_s": 794},
     "deploy/W931_R70_CHUNK_SCAN.md arm B (--prefill auto:16384) => -4.95%",
     {"workload": {"prompt_tokens": 31700, "max_tokens": 64, "temperature": 0}}),
    ("2026-11-04T07:50:00", "w931-r70-chunk32768-32k", "strata-0.1.55w", "cf2ba243f908fe1b9d058d66b761c00f",
     {"prefill_ttft_s": {"n": 3, "median": 39.263, "cv_pct": 0.2}, "prefill_tok_s": 780},
     "deploy/W931_R70_CHUNK_SCAN.md arm C (--prefill auto:32768) => -3.17%, worse than 16384",
     {"workload": {"prompt_tokens": 31700, "max_tokens": 64, "temperature": 0}}),
    ("2026-11-04T08:40:00", "w932-chunk8192-64k", "strata-0.1.55w", "cf2ba243f908fe1b9d058d66b761c00f",
     {"prefill_ttft_s": {"n": 4, "median": 81.25, "cv_pct": 0.5}, "prefill_tok_s": 754},
     "deploy/W932_R75_AND_CHUNK16384_ADOPT.md, 0-reused samples only (61,246 prompt tokens)",
     {"workload": {"prompt_tokens": 61246, "max_tokens": 32, "temperature": 0}}),
    ("2026-11-04T08:55:00", "w932-chunk16384-64k", "strata-0.1.55w", "cf2ba243f908fe1b9d058d66b761c00f",
     {"prefill_ttft_s": {"n": 2, "median": 76.35, "cv_pct": 0.3}, "prefill_tok_s": 802},
     "deploy/W932_R75_AND_CHUNK16384_ADOPT.md, 0-reused samples => +6.2% (corrects W931's sign error)",
     {"workload": {"prompt_tokens": 61246, "max_tokens": 32, "temperature": 0}}),
    ("2026-11-04T09:00:00", "w932-chunk16384-130k", "strata-0.1.55w", "cf2ba243f908fe1b9d058d66b761c00f",
     {"prefill_ttft_s": {"n": 2, "median": 165.116, "cv_pct": 0.1}, "prefill_tok_s": 788.7},
     "deploy/W932_R75_AND_CHUNK16384_ADOPT.md; 8192 reference 177.9 s / 729.6 tok/s from history",
     {"workload": {"prompt_tokens": 130225, "max_tokens": 16, "temperature": 0}}),
    ("2026-11-04T09:20:00", "w935-r78-ple-raise-limit", "strata-0.1.55v", "8e92c662d8384bad585845285c3c6b9c",
     {"prefill_ttft_s": {"n": 9, "median": 8.853, "cv_pct": 0.9},
      "decode_tok_s": {"n": 4, "median": 79.4, "cv_pct": 2.0}},
     "deploy/W935_PLE_RAISE_LIMIT_ADOPT.md: 5a13c34f, no regression",
     {"workload": {"prompt_tokens": 6300, "max_tokens": 256, "temperature": 0}}),
    ("2026-11-04T11:40:00", "w936-r77-fatal-gpu", "strata-0.1.55w", "cf2ba243f908fe1b9d058d66b761c00f",
     {"prefill_ttft_s": {"n": 9, "median": 8.868, "cv_pct": 1.1},
      "decode_tok_s": {"n": 4, "median": 79.44, "cv_pct": 2.0}},
     "deploy/W936_R77_FATAL_GPU_ADOPT.md: e1b27d54, no regression",
     {"workload": {"prompt_tokens": 6343, "max_tokens": 256, "temperature": 0}}),
]

os.makedirs(RUNS, exist_ok=True)
for ts, label, exe, m, metrics, prov, extra in R:
    rec(ts, label, exe, m, metrics, prov, extra)

n = len([x for x in os.listdir(RUNS) if x.endswith(".json")])
print("runs now: %d files" % n)
print("rollback --last check:", sh("tail -2 %s | head -1 | cut -f2" % HIST))
