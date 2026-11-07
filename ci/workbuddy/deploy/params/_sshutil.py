# -*- coding: utf-8 -*-
"""
_sshutil.py —— 本机 -> 166 通道的固化实现（routeK 项目）

存在理由（踩坑史，禁重复）：
  - 本机 Bash shim 会打坏 `ssh '...'` 命令行（banner exchange: Connection to UNKNOWN port -1），
    故一律用 `subprocess.run(["ssh", ...argv])`，argv 不经 shell。
  - stdin 传 str 会被翻成 CR+LF => 远端整批 127。故一律传 bytes 并断言无 CR。
  - 远端脚本若含引号嵌套极易碎 => 一律 base64 编码，远端 `base64 -d | bash`。
  - 取回二进制/base64 时，`"".join(x.encode().split())` 会抛
    `TypeError: sequence item 0: expected str instance, bytes found`
    （本项目已复发三次：r122 / r123 / r160）=> **拼接一律用 b""**.

对外只用三个函数：
  run_remote(script, timeout)      -> (rc, stdout, stderr)
  fetch_b64(remote_path, local_path) -> (ok, size, md5, detail)
  push_b64(local_path, remote_path)  -> (ok, size, md5, detail)
"""

import base64
import hashlib
import os
import subprocess

HOST = "albus@192.168.50.166"
SSH_OPTS = ["-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "-o", "ServerAliveInterval=15"]

# [!] 2026-10-01 实测：本机 PATH 里 `ssh` 解析到 Windows OpenSSH
#   (C:\Program Files\OpenSSH\ssh.exe), 它在 PowerShell 起的子进程里
#   **任何真实连接都失败**：rc=-1，stderr = `pipe(notify_pipe) failed Unknown error`
#   + `poll: Not enough space`（`ssh -V` 正常，所以只看版本号会误判成通道没问题）。
#   Git 自带的 ssh.exe 三种 stdin 模式全部正常 => **显式钉死，禁止走 PATH 解析**。
SSH_BIN = "C:/Program Files/Git/usr/bin/ssh.exe"


def run_remote(script, timeout=300, host=HOST):
    """把 script（str）以 base64 通道发到远端执行。返回 (rc, stdout, stderr)。"""
    data = script.encode("utf-8")
    if b"\r" in data:
        raise ValueError("SCRIPT_HAS_CR")
    p = subprocess.run(
        [SSH_BIN] + SSH_OPTS + [host, "base64 -d | bash"],
        input=base64.b64encode(data),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def _join_b64(blob_text):
    """关键：一律 bytes 拼接。"""
    return b"".join(blob_text.encode("ascii", "ignore").split())


def fetch_b64(remote_path, local_path, timeout=300, host=HOST):
    """取回远端文件（base64 通道）。返回 (ok, size, md5, detail)。"""
    script = (
        "set -u\n"
        "F=%s\n"
        "if [ ! -f \"$F\" ]; then echo 'FETCH_MISSING=1'; exit 3; fi\n"
        "echo \"SIZE=$(stat -c %%s \"$F\")\"\n"
        "echo \"MD5=$(md5sum \"$F\" | cut -d' ' -f1)\"\n"
        "echo '---B64---'\n"
        "base64 -w0 \"$F\"\n"
        "echo ''\n"
        "echo '---B64END---'\n" % _q(remote_path)
    )
    rc, out, err = run_remote(script, timeout=timeout, host=host)
    if "FETCH_MISSING=1" in out or "---B64---" not in out or "---B64END---" not in out:
        return False, -1, "", "FETCH_STRUCT_FAIL rc=%d err=%s" % (rc, err.strip()[:300])
    blob = out.split("---B64---", 1)[1].split("---B64END---", 1)[0]
    try:
        raw = base64.b64decode(_join_b64(blob))
    except Exception as e:
        return False, -1, "", "B64_DECODE_FAIL %r" % (e,)
    d = os.path.dirname(local_path)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    with open(local_path, "wb") as f:
        f.write(raw)
    md5 = hashlib.md5(raw).hexdigest()
    rsize = None
    for line in out.split("\n"):
        if line.startswith("SIZE="):
            rsize = int(line.split("=", 1)[1].strip() or -1)
        if line.startswith("MD5="):
            rmd5 = line.split("=", 1)[1].strip()
    ok = (rsize == len(raw)) and (rmd5 == md5)
    return ok, len(raw), md5, "remote_size=%s remote_md5=%s match=%s" % (rsize, rmd5, ok)


def push_b64(local_path, remote_path, timeout=300, host=HOST):
    """推送本机文件到远端（base64 通道 + 远端三验）。返回 (ok, size, md5, detail)。"""
    raw = open(local_path, "rb").read()
    md5 = hashlib.md5(raw).hexdigest()
    b64 = base64.b64encode(raw).decode("ascii")
    script = (
        "set -u\n"
        "D=%s\n"
        "mkdir -p \"$(dirname \"$D\")\"\n"
        "base64 -d > \"$D\" <<'__RK_B64_EOF__'\n"
        "%s\n"
        "__RK_B64_EOF__\n"
        "echo \"R_SIZE=$(stat -c %%s \"$D\")\"\n"
        "echo \"R_MD5=$(md5sum \"$D\" | cut -d' ' -f1)\"\n"
        "bash -n \"$D\" 2>/dev/null && echo 'R_BASHSYNTAX=OK' || echo 'R_BASHSYNTAX=NA_or_FAIL'\n"
        "echo \"R_CR=$(tr -cd '\\r' < \"$D\" | wc -c)\"\n"
        "echo \"R_LF=$(tr -cd '\\n' < \"$D\" | wc -c)\"\n" % (_q(remote_path), b64)
    )
    rc, out, err = run_remote(script, timeout=timeout, host=host)
    rsize = rmd5 = None
    for line in out.split("\n"):
        if line.startswith("R_SIZE="):
            rsize = int(line.split("=", 1)[1].strip() or -1)
        if line.startswith("R_MD5="):
            rmd5 = line.split("=", 1)[1].strip()
    ok = (rsize == len(raw)) and (rmd5 == md5)
    return ok, len(raw), md5, "rc=%d remote_size=%s remote_md5=%s match=%s\n%s" % (
        rc, rsize, rmd5, ok, out.strip()[:1200])


def _q(s):
    """远端路径加单引号（路径内无单引号的前提）。"""
    if "'" in s:
        raise ValueError("PATH_HAS_QUOTE")
    return "'" + s + "'"


def sha_of_bytes(b):
    return hashlib.md5(b).hexdigest()
