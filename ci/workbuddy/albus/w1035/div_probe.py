#!/usr/bin/env python3
"""R95 候选④（tile/填充地板）判别：同长度、不同路由分散度，n=5，交错。

预测（④ 成立时）：低分散提示 → 参与专家更少 → 每条 (专家,tile) 的开销更少
                 ⇒ 同长度下 wall 更低（固定项随"专家数×tile 数"变，与 token 数无关）。
反预测（④ 不成立）：两者墙钟在 2×CV 带内不可分辨。

控制：同一 18 词表；低分散 = 同一短语重复，高分散 = 同词数随机词序；
      每轮都换 seed（内容全新，避开 prompt cache）；A/B 交错各 5 次。
"""
import io
import json
import random
import re
import statistics as st
import subprocess
import sys
import time
import urllib.request

C = "strata166-407"
OUT = "/home/albus/strata166/tmp/w1035/div_probe.log"
V = ("alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike november oscar "
     "papa quebec romeo sierra").split()
REPEAT = 108          # 18 词 × 108 ≈ 1944 词


def log(s):
    line = "%s %s" % (time.strftime("%H:%M:%S"), s)
    print(line, flush=True)
    with io.open(OUT, "a", encoding="utf-8", newline="\n") as f:
        f.write(line + "\n")


def last_done():
    r = subprocess.run("docker logs --tail 40 %s 2>&1 | grep 'done:' | tail -1" % C,
                       shell=True, capture_output=True, text=True)
    return r.stdout.strip()


def ask(prompt):
    body = json.dumps({"model": "x", "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": 4, "temperature": 0.0}).encode()
    req = urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    d = json.loads(urllib.request.urlopen(req, timeout=300).read())
    wall = time.time() - t0
    line = last_done()
    hit = re.search(r"expert cache ([\d.]+)% hit", line)
    pc = re.search(r"\+([\d.]+)% of the routed", line)
    return dict(tok=d.get("usage", {}).get("prompt_tokens"), wall=wall,
                hit=float(hit.group(1)) if hit else None,
                pcie=float(pc.group(1)) if pc else None)


def main():
    rows = {"hi": [], "lo": []}
    for i in range(5):
        for tag in ("hi", "lo"):
            rng = random.Random(91000 + i * 7 + (0 if tag == "hi" else 3))
            if tag == "hi":
                p = " ".join(rng.choice(V) for _ in range(18 * REPEAT))
            else:
                seq = V[:18]
                rng.shuffle(seq)
                p = (" ".join(seq) + " ") * REPEAT
            r = ask(p)
            r["ms_per_ktok"] = r["wall"] * 1000.0 / (r["tok"] / 1000.0)
            rows[tag].append(r)
            log("%-2s #%d tok=%s wall=%.2fs hit=%s pcie=%s  %.0f ms/ktok"
                % (tag, i, r["tok"], r["wall"], r["hit"], r["pcie"], r["ms_per_ktok"]))
    log("== 汇总 ==")
    for tag in ("hi", "lo"):
        v = rows[tag]
        toks = [x["tok"] for x in v]
        per = [x["ms_per_ktok"] for x in v]
        m = st.mean(per)
        cv = st.stdev(per) / m * 100 if len(per) > 1 else 0
        log("%-3s n=%d tok 均值 %.0f (min %d max %d)  %0.0f ms/ktok  CV %.1f%%"
            % (tag, len(v), st.mean(toks), min(toks), max(toks), m, cv))
    a = [x["ms_per_ktok"] for x in rows["lo"]]
    b = [x["ms_per_ktok"] for x in rows["hi"]]
    ma, mb = st.mean(a), st.mean(b)
    ca = st.stdev(a) / ma * 100 if len(a) > 1 else 0
    cb = st.stdev(b) / mb * 100 if len(b) > 1 else 0
    band = 2 * max(ca, cb)
    log("DELTA lo vs hi = %+.1f%%  (2xCV=%.1f%%)  => %s"
        % ((ma / mb - 1) * 100, band,
           "超带（④ 有支持）" if abs((ma / mb - 1) * 100) > band else "带内（④ 未获支持）"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
