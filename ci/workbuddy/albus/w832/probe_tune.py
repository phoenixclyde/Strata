#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W832 探针：确认 strata_tune 是否真的落到引擎（不停服）。

判据不用计时，用引擎自己打的 `drafts accepted A of B`：
spec_min_p 越小 -> 每窗口接受的草稿越多 -> B 越大；越大 -> B 越小。
"""
import json, re, sys, time, urllib.request, io

BASE = "http://127.0.0.1:8090"
LOG = "/data/strata-huihui-ud-iq4_xs.log"

PROMPT = ("下面是一段测试文本，请逐字复述最后一句："
          "在深秋的清晨，海面上浮着一层薄雾，远处的灯塔忽明忽暗。"
          "复述：")

def ask(tune, max_tokens=128, seed=7):
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
    try:
        r = urllib.request.urlopen(req, timeout=180)
        d = json.load(r)
        return time.time() - t0, d, None
    except urllib.error.HTTPError as e:
        return time.time() - t0, None, "HTTP %s: %s" % (e.code, e.read()[:200].decode("utf-8", "replace"))

def tail_log(nbytes=4000):
    with open(LOG, "rb") as f:
        f.seek(0, 2)
        size = f.tell()
        f.seek(max(0, size - nbytes))
        return f.read().decode("utf-8", "replace")

def last_acc(text):
    m = re.findall(r"drafts accepted (\d+) of (\d+)", text)
    return m[-1] if m else None

print("=== 探针开始 ===")
for label, tune in [("default", None),
                    ("minp=0.10", {"spec_min_p": 0.10}),
                    ("minp=0.95", {"spec_min_p": 0.95})]:
    dt, d, err = ask(tune)
    time.sleep(0.4)
    log = tail_log()
    acc = last_acc(log)
    usage = (d or {}).get("usage") or {}
    print("%-10s wall=%5.2fs  accepted=%s  completion=%s  err=%s"
          % (label, dt, acc, usage.get("completion_tokens"), err))
