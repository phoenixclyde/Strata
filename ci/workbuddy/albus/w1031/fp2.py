#!/usr/bin/env python3
"""fp2 -- 48-token greedy fingerprint, rebuilt 2026-11-07 after the power cycle wiped /tmp.

The old script (W1030) is gone and its prompts were not stored in the JSON, so this is a NEW set:
same three shapes (short / en2k / zh2k), same greedy 48 tokens, prompts generated here so they can
be reproduced from this file alone. Record a baseline on the production engine first, then every
candidate arm is compared against that.

usage: fp2.py <label>
"""
import json, sys, time, urllib.request

URL = "http://127.0.0.1:8090/v1/chat/completions"

BODY_EN = ("The committee reviewed the proposal for a new library in the eastern district. "
           "Several members asked about the budget, the timeline, and the expected number of visitors. "
           "The chair noted that the current building was opened in nineteen sixty-two and that its roof "
           "had been repaired twice in the past decade. ")  # ~ 70 tokens per copy

BODY_ZH = ("这段材料主要说明量化推理在显存带宽受限时的表现。作者先比较了不同长度的提示，"
           "然后给出了内核调度与权重换入的实测数据，并指出混合专家模型还需要额外处理路由和缓存。")

def prompt_short():
    return "Answer in one sentence: why does the sky appear blue during the day?"

def prompt_en2k():
    return "Read the following text and then answer in one sentence: what did the committee review?\n\n" + BODY_EN * 14

def prompt_zh2k():
    return "读下面这段话，然后用一句话说明它主要讲什么。\n\n" + BODY_ZH * 26

CASES = [("short", prompt_short), ("en2k", prompt_en2k), ("zh2k", prompt_zh2k)]

def call(prompt, n=48):
    body = json.dumps({
        "model": "x",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": n,
        "temperature": 0,
        "top_k": 1,
        "stream": False,
    }).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.loads(r.read())
    wall = time.time() - t0
    ch = (d.get("choices") or [{}])[0]
    msg = ch.get("message") or {}
    return d, msg, wall

def main():
    label = sys.argv[1] if len(sys.argv) > 1 else "arm"
    out = {"label": label, "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "cases": {}}
    for name, fn in CASES:
        d, msg, wall = call(fn())
        text = msg.get("content") or ""
        reason = msg.get("reasoning_content") or ""
        u = d.get("usage") or {}
        out["cases"][name] = {
            "prompt_tokens": u.get("prompt_tokens"),
            "completion_tokens": u.get("completion_tokens"),
            "wall_s": round(wall, 3),
            "text": text,
            "reasoning_len": len(reason),
            "reasoning": reason,
        }
        shown = (reason or text).replace("\n", " ")[:70]
        print("%-6s ptok=%-5s ctok=%-4s %.2fs | %s" % (
            name, u.get("prompt_tokens"), u.get("completion_tokens"), wall, shown))
    p = "/home/albus/strata166/ci/state/cfg/greedy_%s.json" % label
    json.dump(out, open(p, "w"), indent=1, ensure_ascii=False)
    print("saved", p)

main()
