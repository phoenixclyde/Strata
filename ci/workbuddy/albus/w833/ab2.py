#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W832/W833 引擎测量（容器内）：decode 8 × 128 tok + read 3 档 × 3 次。"""
import json, os, re, sys, time, urllib.request

BASE = "http://127.0.0.1:8090"
LOG = sys.argv[1] if len(sys.argv) > 1 else "/data/w833_arm.log"
TAG = sys.argv[2] if len(sys.argv) > 2 else "arm"
DEC_REPS = int(os.environ.get("DEC_REPS", "8"))
RD_REPS = int(os.environ.get("RD_REPS", "3"))

FILLER = ("深秋的清晨，海面上浮着一层薄雾，远处的灯塔忽明忽暗，潮声一阵一阵地涌来，"
          "岸边礁石被浪拍得发白，几只海鸟贴着水面掠过。")

RE_LINE = re.compile(
    r"prompt (\d+) tokens = (\d+) reused \+ (\d+) read in (\d+) ms \(([\d.]+) tok/s\), "
    r"(\d+) generated in (\d+) ms \(([\d.]+) tok/s\)")


def pos():
    try:
        return os.path.getsize(LOG)
    except OSError:
        return 0


def since(p):
    try:
        with open(LOG, "rb") as f:
            f.seek(p)
            return f.read().decode("utf-8", "replace")
    except OSError:
        return ""


def ask(text, max_tokens, seed=5):
    body = {"messages": [{"role": "user", "content": text}],
            "max_tokens": max_tokens, "temperature": 0, "seed": seed}
    req = urllib.request.Request(BASE + "/v1/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    r = urllib.request.urlopen(req, timeout=300)
    d = json.load(r)
    return time.time() - t0, d


def one(text, max_tokens, note):
    p = pos()
    wall, d = ask(text, max_tokens)
    time.sleep(0.2)
    m = RE_LINE.findall(since(p))
    rec = {"arm": TAG, "note": note, "wall_s": round(wall, 3),
           "completion": (d.get("usage") or {}).get("completion_tokens")}
    if m:
        g = m[-1]
        rec.update({"prompt_tokens": int(g[0]), "reused": int(g[1]), "read_ms": int(g[3]),
                    "read_tps": float(g[4]), "gen_n": int(g[5]), "gen_ms": int(g[6]),
                    "gen_tps": float(g[7])})
    print(json.dumps(rec, sort_keys=True), flush=True)
    return rec


def main():
    print("# arm", TAG, "decode_reps", DEC_REPS, "read_reps", RD_REPS, flush=True)
    for i in range(3):
        ask("预热" + str(i) + "：请数三个数。", 256, seed=90 + i)
    print("# warm-up done", flush=True)

    for i in range(DEC_REPS):
        one("请用一段话描写秋天，不要标题。", 128, "decode")

    for approx in (1300, 2500, 4500):
        reps = max(1, approx // 30)
        for j in range(RD_REPS):
            text = (FILLER * reps) + "（编号%d-%d）" % (approx, j) + "请只回答：好。"
            one(text, 1, "read%d" % approx)
    print("# done", flush=True)


if __name__ == "__main__":
    main()
