#!/usr/bin/env python3
"""R95 候选① 零停机判别：同长度、不同缓存状态下的 prefill 墙钟 vs PCIe 占比。

原理：引擎在每条请求的日志行里自报
    done: N tokens in X s (Y tok/s) … expert cache Z% hit (+W% of the routed experts over PCIe)
若固定项是「权重搬运」，则 W（走 PCIe 的专家比例）高时 prefill 应显著更慢，且慢的幅度与 W 成比例；
若固定项与 W 无关，则候选① 被证伪。

做法：两批各 6 条、长度相同（≈2K）、内容全新（每批都换词序）：
  批1 = 冷（刚启动的缓存状态，PCIe 占比应高）
  批2 = 温（批1 已把大量专家拉进 VRAM，PCIe 占比应低）
不重启、不改配置，只在生产上发普通请求。
"""
import io
import json
import random
import re
import subprocess
import sys
import time
import urllib.request

C = "strata166-407"
OUT = "/home/albus/strata166/tmp/w1035/pcie_share.log"

V = ("alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike november oscar papa "
     "quebec romeo sierra tango uniform victor whiskey xray yankee zulu red green blue cyan magenta yellow "
     "black white orange purple silver golden copper north south east west up down left right front back "
     "inner outer river stone cloud forest metal glass paper cotton salt pepper sugar lemon olive coral "
     "ivory amber ruby jade onyx pearl quartz topaz cobalt indigo violet crimson scarlet azure navy teal").split()


def log(s):
    line = "%s %s" % (time.strftime("%H:%M:%S"), s)
    print(line, flush=True)
    with io.open(OUT, "a", encoding="utf-8", newline="\n") as f:
        f.write(line + "\n")


def last_done():
    r = subprocess.run("docker logs --tail 30 %s 2>&1 | grep 'done:' | tail -1" % C,
                       shell=True, capture_output=True, text=True)
    return r.stdout.strip()


def ask(prompt, seed):
    body = json.dumps({"model": "x", "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": 4, "temperature": 0.0}).encode()
    req = urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    d = json.loads(urllib.request.urlopen(req, timeout=300).read())
    wall = time.time() - t0
    line = last_done()
    m_tok = re.search(r"done: (\d+) tokens in ([\d.]+) s", line)
    m_hit = re.search(r"expert cache ([\d.]+)% hit", line)
    m_pc = re.search(r"\+([\d.]+)% of the routed experts over PCIe", line)
    return dict(seed=seed, pt=d.get("usage", {}).get("prompt_tokens"), wall=wall,
                gen_tok=int(m_tok.group(1)) if m_tok else None,
                gen_s=float(m_tok.group(2)) if m_tok else None,
                hit=float(m_hit.group(1)) if m_hit else None,
                pcie=float(m_pc.group(1)) if m_pc else None)


def main():
    rows = []
    for batch in (1, 2):
        for i in range(6):
            rng = random.Random(700000 + batch * 100 + i)     # 每批词序不同 ⇒ 内容全新
            prompt = " ".join(rng.choice(V) for _ in range(1600))
            r = ask(prompt, (batch, i))
            rows.append((batch, r))
            log("batch%d #%d prompt_tokens=%s wall=%.2fs hit=%s pcie=%s"
                % (batch, i, r["pt"], r["wall"], r["hit"], r["pcie"]))
    print("\n批  tokens  wall    hit%   pcie%", flush=True)
    stat = {}
    for b, r in rows:
        stat.setdefault(b, []).append(r)
    for b in sorted(stat):
        v = stat[b]
        w = [x["wall"] for x in v]
        h = [x["hit"] for x in v if x["hit"] is not None]
        p = [x["pcie"] for x in v if x["pcie"] is not None]
        log("batch%d n=%d wall mean=%.2fs (min %.2f max %.2f)  hit mean=%.1f%%  pcie mean=%.1f%%"
            % (b, len(v), sum(w) / len(w), min(w), max(w),
               sum(h) / len(h) if h else -1, sum(p) / len(p) if p else -1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
