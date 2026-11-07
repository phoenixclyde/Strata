# -*- coding: utf-8 -*-
"""W930e: 上游描述的核心症状 —— 新任务返回旧答案。

turn1 让模型给出一段 JSON 配置；turn2 换成完全不同的任务（写 Python 函数）。
若 penalty 把 turn1 的答案留在窗口里并惩罚它，模型可能"逃回"旧答案。
判据：turn2 的输出是否含 def/return（Python）而非 {/"service"（JSON）。
"""
import json, urllib.request

URL = "http://127.0.0.1:8090/v1/chat/completions"

TURN1 = ("Write a small JSON config for a service named alpha: it needs a port, replicas and a region. "
         "Output only the JSON.")
TURN2 = ("Different task now. Write a Python function add(a, b) that returns the sum. "
         "Output only the code.")


def post(messages, pp, maxtok=120):
    body = {"model": "x", "messages": messages, "max_tokens": maxtok,
            "temperature": 0, "presence_penalty": pp,
            "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.loads(r.read())
    return (d["choices"][0]["message"].get("content") or ""), d["choices"][0].get("finish_reason")


def classify(txt):
    low = txt.lower()
    is_py = ("def " in low) or ("return" in low and "(" in txt)
    is_json = '"service"' in low or '"port"' in low or ("{" in txt and "alpha" in low)
    if is_py and not is_json:
        return "PYTHON(ok)"
    if is_json and not is_py:
        return "**JSON(旧答案)**"
    if is_py and is_json:
        return "BOTH"
    return "OTHER"


for pp in (0.0, 1.5, 10.0):
    print("=" * 62)
    print("presence_penalty = %s" % pp)
    bad = 0
    for i in range(3):
        msgs = [{"role": "user", "content": TURN1}]
        a1, _ = post(msgs, pp, maxtok=100)
        msgs.append({"role": "assistant", "content": a1})
        msgs.append({"role": "user", "content": TURN2})
        a2, fr = post(msgs, pp)
        cls = classify(a2)
        if "旧答案" in cls:
            bad += 1
        print("  rep%d: %-14s %s" % (i + 1, cls, a2.replace("\n", " ")[:80]))
    print("  -> 返回旧答案 %d/3" % bad)
