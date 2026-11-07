#!/usr/bin/env python3
"""强制截断版：turn1 用很小的 max_tokens，让回答被截断，
这样最后一个 verify window 会 park 客户端没收到的 token —— 正是 #4677 的触发条件。"""
import json, random, subprocess, sys, urllib.request

BASE = "http://127.0.0.1:8090"
LOG = "/data/strata-huihui-ud-iq4_xs.log"
CONTAINER = "strata166-407"

WORDS = ("alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima "
         "mike november oscar papa quebec romeo sierra tango uniform victor whiskey "
         "xray yankee zulu system kernel memory buffer thread process device driver "
         "network packet socket stream channel vector matrix tensor scalar linear").split()


def log_lines():
    return int(subprocess.run(["docker", "exec", CONTAINER, "wc", "-l", LOG],
                              capture_output=True, text=True).stdout.split()[0])


def prompt_lines(start):
    out = subprocess.run(["docker", "exec", CONTAINER, "sh", "-c",
                          "awk 'NR>%d' %s | grep -E 'strata serve: prompt '" % (start, LOG)],
                         capture_output=True, text=True).stdout
    return [l for l in out.strip().split("\n") if l.strip()]


def chat(messages, max_tokens):
    body = json.dumps({"model": "x", "messages": messages, "max_tokens": max_tokens,
                       "temperature": 0}).encode()
    req = urllib.request.Request(BASE + "/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r:
        return json.loads(r.read())["choices"][0]["message"].get("content") or ""


def parse(lines):
    for l in lines:
        if "strata serve: prompt " in l:
            seg = l.split("strata serve: prompt ", 1)[1]
            n = int(seg.split(" tokens")[0])
            m = int(seg.split("= ")[1].split(" reused")[0])
            return n, m
    return None


def run(tag, nconv=4, nwords=5000, cap=200):
    print("=== %s: %d 段 x 2 轮, ~%d words, turn1 max_tokens=%d（强制截断）===" % (tag, nconv, nwords, cap))
    out = []
    for c in range(1, nconv + 1):
        p1 = (" ".join(random.choice(WORDS) for _ in range(nwords)) +
              "\n\nWrite a detailed 900-word technical analysis of the passage above.")
        m1 = [{"role": "user", "content": p1}]
        s0 = log_lines(); a1 = chat(m1, cap); t1 = prompt_lines(s0)

        m2 = m1 + [{"role": "assistant", "content": a1},
                   {"role": "user", "content": "Now summarize the whole discussion in one sentence."}]
        s1 = log_lines(); a2 = chat(m2, 128); t2 = prompt_lines(s1)

        r1, r2 = parse(t1), parse(t2)
        if r2:
            pct = 100.0 * r2[1] / r2[0]
            out.append(pct)
            print("  conv%d  turn1=%s tok | turn2=%d tok, %d reused = %.2f%%  (answer1 %d chars)"
                  % (c, r1[0] if r1 else "?", r2[0], r2[1], pct, len(a1)))
        else:
            print("  conv%d  parse failed" % c)
    if out:
        print("  reuse%%: %s" % " ".join("%.2f" % v for v in out))
        print("  median %.2f%%  min %.2f%%  <99%% 的段数 %d/%d"
              % (sorted(out)[len(out) // 2], min(out), sum(1 for v in out if v < 99.0), len(out)))


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "arm")
