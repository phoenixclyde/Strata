#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w861_push_doc_safe.py -- 带权限预检的推送脚本（W861 复盘后的改正版）。

对比旧版 push_doc.py 的两处缺陷：
  1. 旧版只 GET contents 判断 404 —— 但 404 可能是「仓库不存在 / 无权限 / 文件不存在」，
     三者区分不了；我第一次 PUT 404 就是无权限，却无法从返回值识别。
  2. 旧版没有权限预检，直接写。

新版流程：
  step 0  GET /user                       确认 token 身份
  step 1  GET /repos/{owner}/{repo}       看 permissions.push —— 为 False 立即停
  step 2  GET contents                    看文件是否已存在（拿 sha 才能更新）
  step 3  PUT                             仅在 step 1 通过后执行
另加 --dry-run：只走到 step 2，不写。
"""
import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
TOKFILE = os.path.join(HERE, "..", "..", "deploy", "tmp", "_tok.txt")


def make_req(tok):
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
    return req


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("owner")
    ap.add_argument("repo")
    ap.add_argument("path")
    ap.add_argument("local_file")
    ap.add_argument("--branch", default=None)
    ap.add_argument("--message", default="docs: update")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    tok = open(TOKFILE, encoding="utf-8").read().strip()
    req = make_req(tok)

    st, me = req("GET", "https://api.github.com/user")
    print("step0 token identity: %s (HTTP %s)" % (me.get("login"), st))

    st, repo = req("GET", "https://api.github.com/repos/%s/%s" % (a.owner, a.repo))
    if st != 200:
        print("step1 FAIL: repo 不可访问 HTTP %s -> %s" % (st, repo.get("message")))
        return 2
    perms = repo.get("permissions") or {}
    print("step1 repo: %s | push=%s | admin=%s"
          % (repo.get("full_name"), perms.get("push"), perms.get("admin")))
    if not perms.get("push"):
        print("step1 FAIL: 没有写权限（push=False），停止。**不要**再试 PUT。")
        return 3

    branch = a.branch or repo.get("default_branch") or "main"
    api = "https://api.github.com/repos/%s/%s/contents/%s" % (a.owner, a.repo, a.path)
    st, js = req("GET", api)
    sha = js.get("sha") if st == 200 else None
    print("step2 contents: HTTP %s | existing sha=%s" % (st, sha))

    if a.dry_run:
        print("dry-run: 到此为止，未写入")
        return 0

    body = open(a.local_file, "rb").read()
    payload = {"message": a.message, "content": base64.b64encode(body).decode(), "branch": branch}
    if sha:
        payload["sha"] = sha
    st, js = req("PUT", api, payload)
    print("step3 PUT: HTTP %s" % st)
    if st in (200, 201):
        print("  commit:", js["commit"]["sha"][:12])
        print("  url   :", js["content"]["html_url"])
        return 0
    print("  ERROR:", json.dumps(js, ensure_ascii=False)[:300])
    return 1


if __name__ == "__main__":
    sys.exit(main())
