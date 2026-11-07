# -*- coding: utf-8 -*-
"""本机 GitHub 通道（复用 W703 已验证的取凭据姿势）。

要点（技能 routeb-github-archive §8.1 + W703 实测）：
  · helper 必须**显式钉**到 `C:/Program Files/Git/mingw64/bin/git-credential-manager.exe`
    （用默认 helper 会长时间不返回）
  · 禁 set GCM_INTERACTIVE；只设 GIT_TERMINAL_PROMPT=0 + GIT_ASKPASS=echo
  · 取回值必须校验 username / 长度 / 前缀，再 GET /user 复验
"""
import json
import os
import subprocess
import time
import urllib.error
import urllib.request

GCM2 = '!"C:/Program Files/Git/mingw64/bin/git-credential-manager.exe"'
TOKF = r"D:/workbuddy_space/strata_ws/waves/_tok.tmp"


def _valid(u, p):
    return (u == "phoenixclyde" and len(p) >= 40 and " " not in p
            and p.startswith(("gho_", "ghp_", "github_pat_")))


def get_token(force=False):
    if not force and os.path.isfile(TOKF):
        t = open(TOKF).read().strip()
        if _valid("phoenixclyde", t):
            return t
    e = dict(os.environ)
    e.update({"GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "echo",
              "GIT_CONFIG_COUNT": "2",
              "GIT_CONFIG_KEY_0": "credential.helper", "GIT_CONFIG_VALUE_0": "",
              "GIT_CONFIG_KEY_1": "credential.helper", "GIT_CONFIG_VALUE_1": GCM2})
    e.pop("GCM_INTERACTIVE", None)
    t0 = time.time()
    r = subprocess.run(["git", "credential", "fill"],
                       input=b"protocol=https\nhost=github.com\n\n",
                       capture_output=True, timeout=60, env=e)
    f = {}
    for ln in r.stdout.decode("utf-8", "replace").split("\n"):
        if "=" in ln:
            k, v = ln.split("=", 1)
            f[k.strip()] = v.strip()
    u, p = f.get("username", ""), f.get("password", "")
    if not _valid(u, p):
        raise SystemExit("TOKEN_INVALID rc=%s elapsed=%.1fs user=%r len=%d prefix=%r"
                         % (r.returncode, time.time() - t0, u, len(p), p[:6]))
    open(TOKF, "w").write(p)
    return p


_PX = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or ""


def api(url, method="GET", payload=None, token=None, timeout=90):
    tok = token or get_token()
    op = urllib.request.build_opener(urllib.request.ProxyHandler({"http": _PX, "https": _PX}))
    hdr = {"User-Agent": "routek-client", "Accept": "application/vnd.github+json",
           "Authorization": "Bearer " + tok}
    data = json.dumps(payload).encode() if payload is not None else None
    if data:
        hdr["Content-Type"] = "application/json"
    rq = urllib.request.Request(url, data=data, headers=hdr, method=method)
    try:
        with op.open(rq, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace"), dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace"), dict(e.headers)
    except Exception as e:
        return -1, "%s: %s" % (type(e).__name__, e), {}


def jload(s):
    try:
        return json.loads(s)
    except Exception:
        return None
