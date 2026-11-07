#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W832 P0-a：单次启动内交替重判 --spec-min-p 与 --pcie-frac。

判据（先声明，只用这一列）：tokens/window ÷ ms/window。
副判据只记录、不用于排序：wall tok/s。

设计：随机区组。每块含每个取值各一次，块内顺序随机 ⇒ 漂移在块内对消。
"""
import json, os, random, re, hashlib, time, urllib.request, urllib.error

BASE = "http://127.0.0.1:8090"
LOG = "/data/w832_tune.log"
OUT = "/data/w832_tune_results.jsonl"
PROMPT = ("下面是一段固定文本，请原样复述："
          "深秋的清晨，海面上浮着一层薄雾，远处的灯塔忽明忽暗，潮声一阵一阵。"
          "复述：")
REPS = 6
MAXTOK = 512

SPEC_VALUES = [0.50, 0.70, 0.85]
PCIE_VALUES = [0.10, 0.20, 0.30]

RE_TIMING = re.compile(
    r"strata decode timing: (\d+) windows, avg T ([\d.]+), ([\d.]+) tokens/window, ([\d.]+) ms/window")
RE_ACC = re.compile(r"drafts accepted (\d+) of (\d+)")


def _log_pos():
    try:
        return os.path.getsize(LOG)
    except OSError:
        return 0


def _log_since(pos):
    try:
        with open(LOG, "rb") as f:
            f.seek(pos)
            return f.read().decode("utf-8", "replace")
    except OSError:
        return ""


def ask(tune, seed=11, max_tokens=MAXTOK):
    body = {
        "messages": [{"role": "user", "content": PROMPT + str(seed)}],
        "max_tokens": max_tokens,
        "temperature": 0,
        "seed": seed,
    }
    if tune:
        body["strata_tune"] = tune
    req = urllib.request.Request(BASE + "/v1/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    r = urllib.request.urlopen(req, timeout=300)
    d = json.load(r)
    wall = time.time() - t0
    parts = []
    for ch in d.get("choices") or []:
        msg = ch.get("message") or {}
        parts.append(msg.get("content") or "")
        parts.append(msg.get("reasoning_content") or "")
    return wall, d, "".join(parts)


def run_one(axis, value, block, retry=2):
    tune = {"spec_min_p": value} if axis == "spec_min_p" else {"pcie_frac": value}
    last_err = None
    for attempt in range(retry + 1):
        try:
            pos = _log_pos()
            wall, d, txt = ask(tune)
            break
        except Exception as e:                      # noqa: BLE001
            last_err = repr(e)[:160]
            time.sleep(2)
    else:
        return {"axis": axis, "value": value, "block": block, "error": last_err}

    time.sleep(0.25)
    chunk = _log_since(pos)
    m = RE_TIMING.findall(chunk)
    a = RE_ACC.findall(chunk)
    usage = d.get("usage") or {}
    rec = {
        "axis": axis, "value": value, "block": block,
        "wall_s": round(wall, 3),
        "windows": int(m[-1][0]) if m else None,
        "avg_t": float(m[-1][1]) if m else None,
        "tok_per_win": float(m[-1][2]) if m else None,
        "ms_per_win": float(m[-1][3]) if m else None,
        "acc": a[-1] if a else None,
        "completion": usage.get("completion_tokens"),
        "sha": hashlib.sha256(txt.encode()).hexdigest()[:12],
    }
    rec["tok_per_ms"] = (round(rec["tok_per_win"] / rec["ms_per_win"], 4)
                         if rec["tok_per_win"] and rec["ms_per_win"] else None)
    rec["wall_tps"] = round((rec["completion"] or 0) / wall, 2)
    return rec


def main():
    print("warm-up (3 x 192 tok, default env)", flush=True)
    for i in range(3):
        try:
            ask(None, seed=100 + i, max_tokens=192)
        except Exception as e:                      # noqa: BLE001
            print("  warmup err", repr(e)[:120], flush=True)
    print("warm-up done\n", flush=True)

    open(OUT, "w").close()
    rnd = random.Random(20261031)
    for axis, values in (("spec_min_p", SPEC_VALUES), ("pcie_frac", PCIE_VALUES)):
        print("### axis", axis, flush=True)
        for b in range(REPS):
            order = values[:]
            rnd.shuffle(order)
            for v in order:
                rec = run_one(axis, v, b)
                if rec.get("error"):
                    print("  b%d %-5.2f ERROR %s" % (b, v, rec["error"]), flush=True)
                else:
                    print("  b%d %-5.2f T=%.2f tok/win=%.2f ms/win=%.2f tok/ms=%.4f wall=%.2f sha=%s"
                          % (b, v, rec["avg_t"] or -1, rec["tok_per_win"] or -1,
                             rec["ms_per_win"] or -1, rec["tok_per_ms"] or -1,
                             rec["wall_s"], rec["sha"]), flush=True)
                with open(OUT, "a") as f:
                    f.write(json.dumps(rec, sort_keys=True) + "\n")
        print("", flush=True)
    print("DONE ->", OUT, flush=True)


if __name__ == "__main__":
    main()
