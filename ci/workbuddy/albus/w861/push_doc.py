#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w861_push_doc.py -- 把 B 线完整调查记录推到 KIntegrated/vllm-gfx906-mobydick。

用 GitHub Contents API（仓库 309 MB，不 clone）：
    GET  /repos/{owner}/{repo}/contents/{path}   看是否已存在（存在则要 sha 才能更新）
    PUT  /repos/{owner}/{repo}/contents/{path}   创建/更新
"""
import base64
import json
import os
import urllib.request
import urllib.error

OWNER = "phoenixclyde"
REPO = "Strata"
PATH = "docs/hipblaslt_gfx906_investigation.md"
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "W861_HIPBLASLT_GFX906.md")
TOKFILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "deploy", "tmp", "_tok.txt")

tok = open(TOKFILE, encoding="utf-8").read().strip()
body = open(SRC, "rb").read()
print("local size:", len(body), "bytes")

API = "https://api.github.com/repos/%s/%s/contents/%s" % (OWNER, REPO, PATH)


def req(method, url, payload=None):
    data = json.dumps(payload).encode() if payload else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Authorization", "Bearer " + tok)
    r.add_header("User-Agent", "w861")
    r.add_header("Accept", "application/vnd.github+json")
    if data:
        r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


sha = None
st, js = req("GET", API)
print("GET:", st, js.get("message", js.get("sha", ""))[:40] if isinstance(js, dict) else "")
if st == 200:
    sha = js["sha"]
    print("existing sha:", sha)

payload = {
    "message": "docs: hipBLASLt on gfx906 (MI50) 完整调查记录 — 20 轮定位到 non-MI codegen 守卫缺失",
    "content": base64.b64encode(body).decode(),
    "branch": "main",
}
if sha:
    payload["sha"] = sha

st, js = req("PUT", API, payload)
print("PUT:", st)
if st in (200, 201):
    print("commit:", js["commit"]["sha"][:12])
    print("url:", js["content"]["html_url"])
else:
    print("ERROR:", json.dumps(js, ensure_ascii=False)[:400])
