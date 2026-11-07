#!/usr/bin/env python3
"""多轮 park 复用测试：4 段长对话，每段 2 轮，记录第 2 轮的 reused 比例。

判据来自上游 #4677 的描述：最后一个 verify window 若 park 了客户端没收到的 token，
快照会被 conversation_prefix() 拒绝而回退到更旧 checkpoint，表现为第 2 轮 reused 变小、read 变大。
"""
import json, random, subprocess, sys, time

BASE = "http://127.0.0.1:8090"
LOG = "/data/strata-huihui-ud-iq4_xs.log"
CONTAINER = "strata166-407"

WORDS = ("alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima "
         "mike november oscar papa quebec romeo sierra tango uniform victor whiskey "
         "xray yankee zulu system kernel memory buffer thread process device driver "
         "network packet socket stream channel vector matrix tensor scalar linear").split()


def log_lines():
    out = subprocess.run(["docker", "exec", CONTAINER, "wc", "-l", LOG],
                         capture_output=True, text=True).stdout.split()[0]
    return int(out)


def new_prompt_lines(start):
    out = subprocess.run(["docker", "exec", CONTAINER, "sh", "-c",
                          "awk 'NR>%d' %s | grep -E 'strata serve: prompt ' " % (start, LOG)],
                         capture_output=True, text=True).stdout
    return [l for l in out.strip().split("\n") if l.strip()]


def chat(messages, max_tokens):
    import urllib.request
    body = json.dumps({"model": "x", "messages": messages, "max_tokens": max_tokens,
                       "temperature": 0}).encode()
    req = urllib.request.Request(BASE + "/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        d = json.loads(r.read())
    return d["choices"][0]["message"].get("content") or ""


def run(tag, nconv=4, nwords=5000):
    print("=== %s: %d 段对话 x 2 轮, prompt ~%d words ===" % (tag, nconv, nwords))
    rows = []
    for c in range(1, nconv + 1):
        p1 = " ".join(random.choice(WORDS) for _ in range(nwords))
        m1 = [{"role": "user", "content": p1}]
        s0 = log_lines()
        a1 = chat(m1, 768)
        t1 = new_prompt_lines(s0)

        m2 = m1 + [{"role": "assistant", "content": a1},
                   {"role": "user", "content": "Summarize the passage above in one short sentence."}]
        s1 = log_lines()
        a2 = chat(m2, 128)
        t2 = new_prompt_lines(s1)

        def parse(lines):
            for l in lines:
                if "strata serve: prompt " in l:
                    # strata serve: prompt N tokens = M reused + K read in ...
                    seg = l.split("strata serve: prompt ", 1)[1]
                    n = int(seg.split(" tokens")[0])
                    m = int(seg.split("= ")[1].split(" reused")[0])
                    return n, m
            return None

        r1, r2 = parse(t1), parse(t2)
        rows.append((c, r1, r2))
        if r2:
            pct = 100.0 * r2[1] / r2[0] if r2[0] else 0.0
            print("  conv%d  turn1=(%s/%s)  turn2=(%d tok, %d reused = %.2f%%)"
                  % (c, r1[1] if r1 else "?", r1[0] if r1 else "?", r2[0], r2[1], pct))
        else:
            print("  conv%d  parse failed: %s" % (c, t2[:2]))

    vals = [100.0 * r[2][1] / r[2][0] for r in rows if r[2]]
    if vals:
        print("  reuse%%: %s" % " ".join("%.2f" % v for v in vals))
        print("  median %.2f%%  mean %.2f%%  min %.2f%%" % (
            sorted(vals)[len(vals) // 2], sum(vals) / len(vals), min(vals)))
    return rows


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "arm")
