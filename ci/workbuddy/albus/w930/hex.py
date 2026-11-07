# -*- coding: utf-8 -*-
"""W930d: 用长十六进制串做高灵敏判据 —— 抄错一个字符即命中。

机制：penalty window 覆盖 prompt 尾部 => 串里每个 token 都被惩罚 => 抄写易出错。
对比 pp = 0 / 1.5（模型卡 instruct 值）/ 10。
"""
import json, re, urllib.request

URL = "http://127.0.0.1:8090/v1/chat/completions"
CHECKSUM = "7F3A9C21DE4B"

TURN1 = ("Here is the deployment record. The checksum field is " + CHECKSUM +
         " and the service is alpha. Acknowledge with just: OK")
TURN2 = ("Output the checksum again, exactly as given, with no other text.")


def post(messages, pp, instr=True, maxtok=48):
    body = {"model": "x", "messages": messages, "max_tokens": maxtok,
            "temperature": 0, "presence_penalty": pp}
    if instr:
        body["chat_template_kwargs"] = {"enable_thinking": False}
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.loads(r.read())
    m = d["choices"][0]["message"]
    return ((m.get("content") or ""), d["choices"][0].get("finish_reason"))


for pp in (0.0, 1.5, 10.0):
    ok = 0
    print("=" * 60)
    print("presence_penalty = %s" % pp)
    for i in range(3):
        msgs = [{"role": "user", "content": TURN1}]
        _, _ = post(msgs, pp, maxtok=16)
        msgs.append({"role": "assistant", "content": "OK"})
        msgs.append({"role": "user", "content": TURN2})
        c, fr = post(msgs, pp)
        hit = CHECKSUM in c.upper().replace(" ", "")
        ok += hit
        print("  rep%d: %s  %s" % (i + 1, "MATCH" if hit else "**WRONG**",
                                   (c.replace("\n", " ")[:80] or "(empty)")))
    print("  -> 正确 %d/3" % ok)
