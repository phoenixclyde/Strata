# -*- coding: utf-8 -*-
"""W930b: penalty 到底生不生效？用极端值做判据。

若 presence_penalty 真的进了引擎，=10 会强烈抑制重复词，输出与 =0 明显不同。
若两者一致 → penalty 未生效（#4590 的 bug 不可能命中）。
"""
import json, sys, urllib.request

URL = "http://127.0.0.1:8090/v1/chat/completions"


def post(pp, thinking=False, maxtok=48):
    body = {
        "model": "x",
        "messages": [{"role": "user",
                      "content": "Repeat the word 'yes' twenty times separated by single spaces. Output nothing else."}],
        "max_tokens": maxtok,
        "temperature": 0,
        "presence_penalty": pp,
    }
    if not thinking:
        body["chat_template_kwargs"] = {"enable_thinking": False}
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.loads(r.read())
    m = d["choices"][0]["message"]
    return (m.get("content") or ""), (m.get("reasoning_content") or ""), d["choices"][0].get("finish_reason")


for thinking in (False, True):
    print("=" * 66)
    print("thinking=%s" % thinking)
    print("=" * 66)
    for pp in (0.0, 10.0):
        c, rc, fr = post(pp, thinking=thinking)
        n_yes = c.lower().count("yes")
        n_rc_yes = rc.lower().count("yes")
        print("pp=%-4s  yes count(content)=%-3d yes count(reasoning)=%-3d finish=%s" % (pp, n_yes, n_rc_yes, fr))
        print("   content: %s" % (c.replace("\n", " ")[:150] if c else "(empty)"))
        if rc:
            print("   reason : %s" % rc.replace("\n", " ")[:110])
