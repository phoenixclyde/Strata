#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1044 zero-downtime preparation for the install window.

Builds the 32K ids set and the long-length yardstick, pushes every artifact to
166, and verifies md5. No GPU work, no production change.
"""
import io
import json
import os
import sys

sys.path.insert(0, r"D:/workbuddy_space/strata_ws/deploy/params")
import _sshutil  # noqa: E402

W = r"D:/workbuddy_space/strata_ws/albus/w1044"
R = "/home/albus/strata166/tmp/w1044"
R2 = "/home/albus/strata166/tmp/w1042"
R1 = "/home/albus/strata166/tmp/w1041"
LEN32 = 32768


def pull(remote):
    rc, out, err = _sshutil.run_remote("cat " + remote, timeout=180)
    if rc != 0:
        raise SystemExit("pull failed %s: %s" % (remote, err[-300:]))
    return out


def put(local, remote, expect_md5=None):
    ok, size, md5, detail = _sshutil.push_b64(local, remote)
    if not ok:
        raise SystemExit("push failed %s: %s" % (remote, detail))
    print("  push %-28s %8d B  %s" % (os.path.basename(remote), size, md5[:12]))
    return md5


def main():
    os.makedirs(W, exist_ok=True)
    print("=== prepare files ===")
    # 1) long-length yardstick: PROMPT_LENS 1K/8K/20K/32K, one ids set
    qq = pull(R2 + "/qq_r103.py")
    old = "PROMPT_LENS = (1000, 8000, 16000, 20000)"
    assert qq.count(old) == 1, "PROMPT_LENS anchor missing"
    qq_long = qq.replace(old, "PROMPT_LENS = (1000, 8000, 20000, 32768)")
    io.open(W + "/qq_long.py", "w", encoding="utf-8", newline="\n").write(qq_long)
    print("  qq_long.py: PROMPT_LENS -> (1000, 8000, 20000, 32768)")

    # 2) same-source extended ids set (periodic repeat; A/C/D share it => relative KL stays comparable)
    d = json.loads(pull(R2 + "/set20k.ids.json"))
    assert len(d["segments"]) == 1 and len(d["segments"][0]["ids"]) == 20000
    ids = (d["segments"][0]["ids"] * 2)[:LEN32]
    assert len(ids) == LEN32
    out = {"version": "w1044-set32k-same-source", "seg_tokens": LEN32,
           "vocab_size": d.get("vocab_size"),
           "segments": [{"name": "long", "ids": ids}]}
    io.open(W + "/set32k.ids.json", "w", encoding="utf-8", newline="\n").write(
        json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print("  set32k.ids.json: 32768 ids from the same 20000-id source (periodic repeat)")

    # 3) timing from W1042 (same arms, same --kv-grow shape; cross-window GUARD only)
    p2 = json.load(io.open(r"D:/workbuddy_space/strata_ws/albus/w1042/p2_stats.json", encoding="utf-8"))
    timing = {}
    for shape, key in (("shape_8000", "8000"), ("shape_16000", "16000")):
        g = p2[shape]["gpu"]
        timing[key] = {"delta_pct": g["delta_pct"], "band_2cv": g["band_2cv"],
                       "source": "W1042 p2_stats.json (cross-window guard only)"}
    io.open(W + "/timing.json", "w", encoding="utf-8", newline="\n").write(
        json.dumps(timing, ensure_ascii=False, indent=1))
    print("  timing.json:", {k: (v["delta_pct"], v["band_2cv"]) for k, v in timing.items()})

    # 4) push
    print("=== push to 166 ===")
    _sshutil.run_remote("mkdir -p " + R, timeout=60)
    files = ["qq_long.py", "set32k.ids.json", "timing.json", "kl_extract.py",
             "window_w1044.sh"]
    for f in files:
        put(W + "/" + f, R + "/" + f)
    for src, dst in [
        (r"D:/workbuddy_space/strata_ws/albus/w1043/cfg_new.json", "cfg_new.json"),
        (r"D:/workbuddy_space/strata_ws/albus/w1043/longctx_needle.py", "longctx_needle.py"),
        (r"D:/workbuddy_space/strata_ws/albus/w1043/judge.py", "judge.py"),
    ]:
        put(src, R + "/" + dst)

    # 5) remote-side copies, then a separate verifier (no nested heredoc)
    S = ("set -e; "
         "cp -f " + R2 + "/cfgP_kvg.json " + R + "/cfgP_kvg.json; "
         "cp -f " + R2 + "/cfgP_attn.json " + R + "/cfgP_attn.json; "
         "cp -f " + R1 + "/cmp_logits.py " + R + "/cmp_logits.py; "
         "echo copies-ok")
    rc, out, err = _sshutil.run_remote(S, timeout=120)
    print(out.strip())
    if rc != 0:
        raise SystemExit("remote copies failed: " + (err or "")[-500:])
    put(W + "/verify_prep.py", R + "/verify_prep.py")
    rc, out, err = _sshutil.run_remote("python3 " + R + "/verify_prep.py", timeout=180)
    print(out[-3500:])
    if rc != 0:
        raise SystemExit("remote verify failed: " + (err or "")[-500:])
    print("PREP_WINDOW: OK (all artifacts on 166, nothing installed)")


if __name__ == "__main__":
    main()
