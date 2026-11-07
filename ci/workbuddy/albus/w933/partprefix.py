#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W933 / R76: auto:16384 下的部分前缀复用。

场景：长文档（~30K tokens）只读一次，第二次只在末尾追加一小段 + 换问题。
turn1 的 prompt = DOC + Q_A；turn2 = DOC + 追加 + Q_B
=> 最长公共前缀 = DOC（约 30K），之后的 Q_A 与追加段分叉。

复用粒度 = chunk 大小：8192 模式向下对齐到 8192 的整数倍，16384 模式对齐到 16384。
预期 16384 少复用约 8192 token。

跑法（宿主机）：python3 partprefix.py <label>
"""
import json
import random
import subprocess
import sys
import time
import urllib.request

BASE = "http://127.0.0.1:8090"
CONTAINER = "strata166-407"
LOG = "/data/strata-huihui-ud-iq4_xs.log"

VOCAB = ("alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima "
         "mike november oscar papa quebec romeo sierra tango uniform victor whiskey "
         "xray yankee zulu system kernel memory buffer thread process device driver "
         "network packet socket stream channel vector matrix tensor scalar linear "
         "gradient entropy lattice cascade harbor lantern meadow nectar onyx prairie").split()

WORDS = int(__import__('os').environ.get('PP_WORDS', '19000'))
SEED = int(__import__('os').environ.get('PP_SEED', '90001'))


def doc(n, seed):
    rnd = random.Random(seed)
    return " ".join(rnd.choice(VOCAB) for _ in range(n))


def log_lines():
    out = subprocess.run(["docker", "exec", CONTAINER, "wc", "-l", LOG],
                         capture_output=True, text=True).stdout.split()
    return int(out[0])


def new_prompts(start):
    out = subprocess.run(["docker", "exec", CONTAINER, "sh", "-c",
                          "awk 'NR>%d' %s | grep -E 'strata serve: prompt ' " % (start, LOG)],
                         capture_output=True, text=True).stdout
    return [l.strip() for l in out.strip().split("\n") if l.strip()]


def ask(prompt, maxtok=24):
    body = json.dumps({"model": "x", "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": maxtok, "temperature": 0,
                       "chat_template_kwargs": {"enable_thinking": False}}).encode()
    req = urllib.request.Request(BASE + "/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=1200) as r:
        d = json.loads(r.read())
    return time.time() - t0, (d["choices"][0]["message"].get("content") or "")


def parse(line):
    """'prompt N tokens = R reused + M read in T ms' -> (N, R, M, T)"""
    import re
    m = re.search(r"prompt (\d+) tokens = (\d+) reused \+ (\d+) read in (\d+) ms", line)
    return tuple(int(x) for x in m.groups()) if m else None


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else "run"
    D = doc(WORDS, SEED)
    print("=== %s : DOC %d words ===" % (label, WORDS))

    qa = "\n\nQuestion A: name one keyword from the text above."
    qb = ("\n\nEditor note: this report was filed in 2026 and revised twice."
          "\n\nQuestion B: name two keywords from the text above.")

    start = log_lines()
    t1, a1 = ask(D + qa)
    time.sleep(1)
    t2, a2 = ask(D + qb)
    time.sleep(1)

    lines = new_prompts(start)
    print("  共 %d 条 prompt 记录" % len(lines))
    for i, l in enumerate(lines, 1):
        p = parse(l)
        if not p:
            print("  [%d] %s" % (i, l[:100]))
            continue
        n, r, m, t = p
        print("  [%d] prompt=%d  reused=%-6d read=%-6d  %.1f%% 耗时 %d ms (%d tok/s)"
              % (i, n, r, m, 100.0 * r / n, t, n * 1000 // max(t, 1)))
    print("  wall: turn1 %.1f s, turn2 %.1f s" % (t1, t2))


if __name__ == "__main__":
    main()
