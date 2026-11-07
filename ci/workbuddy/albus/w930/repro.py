# -*- coding: utf-8 -*-
"""W930: 在现有生产二进制上验证 #4590 的 bug 是否复现。

设计：turn1 把数字 7391 写进历史，turn2 要求"用同一个 7391"。
若 penalty window 覆盖 prompt 尾部，7391 会被惩罚，模型倾向输出别的数字。

两臂：presence_penalty=0（无 penalty） vs 1.5（模型卡 instruct 默认）。各 3 rep。
"""
import json, sys, time, urllib.request

URL = "http://127.0.0.1:8090/v1/chat/completions"


def post(messages, pp, maxtok=64, temp=0):
    body = {
        "model": "x",
        "messages": messages,
        "max_tokens": maxtok,
        "temperature": temp,
        "presence_penalty": pp,
    }
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.loads(r.read())
    dt = time.time() - t0
    m = d["choices"][0]["message"]
    txt = (m.get("content") or "") + "|" + (m.get("reasoning_content") or "")
    return txt, dt, d["choices"][0].get("finish_reason")


TURN1 = ("Here is a deployment config as JSON: "
         '{"service": "alpha", "port": 7391, "replicas": 3, "region": "eu-west"}. '
         "Acknowledge with just: OK")

TURN2 = ('Now output the same config JSON but change "service" to "bravo" and '
         '"region" to "us-east". Keep the port exactly as it was.')


def run(pp, reps=3):
    print("=" * 66)
    print("presence_penalty = %s" % pp)
    print("=" * 66)
    hits = 0
    for i in range(reps):
        msgs = [{"role": "user", "content": TURN1}]
        a1, dt1, f1 = post(msgs, pp, maxtok=32)
        msgs.append({"role": "assistant", "content": "OK"})
        msgs.append({"role": "user", "content": TURN2})
        a2, dt2, f2 = post(msgs, pp, maxtok=96)
        ok = "7391" in a2
        hits += ok
        # 抽 port 附近的片段
        import re
        m = re.search(r'"?port"?\s*[:=]\s*"?(\d+)', a2)
        got = m.group(1) if m else "(no port)"
        print("rep%d: port=%s  %s  (turn2 %.1fs, finish=%s)" % (
            i + 1, got, "OK" if ok else "**WRONG**", dt2, f2))
        if not ok:
            frag = a2.replace("\n", " ")[:180]
            print("       片段: %s" % frag)
    print("-> 正确 %d/%d" % (hits, reps))
    return hits


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    if which in ("0", "both"):
        run(0.0)
    if which in ("15", "both"):
        run(1.5)
