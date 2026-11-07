# -*- coding: utf-8 -*-
"""W930c: 模型卡的 instruct presence_penalty=1.5 是否自动注入（不显式传时）？

判据：同一 prompt、instruct 模式、不传 presence_penalty。
若重复被抑制（yes 少于 ~18） => 模型卡 1.5 生效 => instruct 用户会命中 #4590。
若完美重复 20 个 => 未注入 => 只有显式传才开。
"""
import json, urllib.request

URL = "http://127.0.0.1:8090/v1/chat/completions"
PROMPT = "Repeat the word 'yes' twenty times separated by single spaces. Output nothing else."


def post(body):
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.loads(r.read())
    m = d["choices"][0]["message"]
    return (m.get("content") or ""), d["choices"][0].get("finish_reason")


cases = [
    ("instruct, 不传 pp（模型卡应为 1.5）", {"chat_template_kwargs": {"enable_thinking": False}}),
    ("instruct, 显式 pp=0（覆盖模型卡）", {"chat_template_kwargs": {"enable_thinking": False}, "presence_penalty": 0}),
    ("instruct, 显式 pp=1.5", {"chat_template_kwargs": {"enable_thinking": False}, "presence_penalty": 1.5}),
]

for label, extra in cases:
    body = {"model": "x", "messages": [{"role": "user", "content": PROMPT}],
            "max_tokens": 64, "temperature": 0}
    body.update(extra)
    c, fr = post(body)
    n = c.lower().count("yes")
    print("%-38s yes=%-3d finish=%-6s  %s" % (label, n, fr, (c.replace("\n", " ")[:90] or "(empty)")))
