#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生产量化快照：镜像 / 引擎 / 参数 / 变量 / 显存 / 缓存 / 实时速率 / 探针。

用法: python3 state_q.py [--no-probe]
"""
import json, re, subprocess, sys, time, urllib.request

C = "strata166-407"
CFG = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"  # host path: run this script ON THE HOST
LOG = "/data/strata-huihui-ud-iq4_xs.log"
PROBE = "--no-probe" not in sys.argv


def sh(cmd, timeout=60):
    p = subprocess.run(["bash", "-lc", cmd], capture_output=True, text=True, timeout=timeout)
    return (p.stdout or "").strip()


def tail(pat, n=1):
    out = sh("docker exec %s bash -lc \"grep -aiE '%s' %s 2>/dev/null | tail -%d\"" % (C, pat, LOG, n))
    return out.split("\n")[-1] if out else ""


print("=" * 66)
print("PRODUCTION SNAPSHOT  %s" % time.strftime("%Y-%m-%d %H:%M:%S"))
print("=" * 66)

print("[容器]  ", sh("docker ps --format '{{.Names}} {{.Status}}' | grep strata166 || echo DOWN"))
print("[镜像]  ", sh("docker inspect %s --format '{{.Config.Image}}'" % C))

c = json.load(open(CFG))
print("[引擎]  ", c["exe"], " args:", len(c["args"]), " env:", len(c.get("env") or {}))
print("[参数]  ", " ".join(c["args"]))
env = c.get("env") or {}
print("[变量]  ", " ".join("%s=%s" % (k.replace("STRATA_", ""), env[k]) for k in sorted(env)))

# 显存
sm = sh("docker exec %s bash -lc 'rocm-smi --showmeminfo vram 2>/dev/null'" % C)
mt = re.search(r"Total Memory \(B\): (\d+)", sm)
mu = re.search(r"Total Used Memory \(B\): (\d+)", sm)
if mt and mu:
    tot, used = int(mt.group(1)), int(mu.group(1))
    print("[显存]   %5.1f / %5.1f GB  used %.1f%%" % (used / 1e9, tot / 1e9, 100.0 * used / tot))

# 缓存 / 借用 / 自适应
m = re.search(r"expert cache (\d+) slots, ([\d.]+) GiB of VRAM", tail("expert cache [0-9]+ slots"))
if m:
    print("[专家缓存] %s slots, %.2f GiB" % (m.group(1), float(m.group(2))))
m = re.search(r"borrows (\d+) CUDA0 cache slots \(([\d.]+) GiB\)", tail("prompt path borrows"))
if m:
    print("[提示借用] %s slots (%.2f GiB)" % (m.group(1), float(m.group(2))))
m = re.search(r"(\d+) rounds, (\d+) experts swapped in, ([\d.]+) ms per round", tail("adaptive tier"))
if m:
    print("[自适应]  %s 轮 / %s 次换入 / %s ms per round" % (m.group(1), m.group(2), m.group(3)))
m = re.search(r"pre-filled (\d+) of (\d+) slots from the profile in ([\d.]+) s \(([\d.]+) MB/s\)",
              tail("pre-filled [0-9]+ of"))
if m:
    print("[预热]   %s/%s slots in %s s (%s MB/s)" % (m.group(1), m.group(2), m.group(3), m.group(4)))

# metrics
try:
    d = json.loads(urllib.request.urlopen("http://127.0.0.1:8090/metrics", timeout=8).read().decode())
    h = d.get("hardware") or {}
    def g(k, fmt="%.1f"):
        v = h.get(k)
        return "-" if v is None else (fmt % v if isinstance(v, (int, float)) else str(v))
    print("[GPU]    util %s%%  temp %sC  power %sW  pcie_rx %s MB/s"
          % (g("gpu_util", "%.0f"), g("gpu_temp", "%.0f"), g("gpu_power", "%.0f"), g("gpu_pcie_rx_mb", "%.2f")))
    print("[速率]   tok_s %s  tok_s_mean %s  prefill_mean %s"
          % (g("tok_s"), g("tok_s_mean"), g("prefill_tok_s_mean", "%.0f")))
    t = d.get("totals") or {}
    if isinstance(t, dict) and t:
        keys = [k for k in ("requests", "prompt_tokens", "completion_tokens", "errors") if k in t]
        print("[累计]  ", {k: t[k] for k in keys} or t)
    lv = d.get("live") or {}
    if isinstance(lv, dict) and lv:
        print("[实时]  ", {k: lv[k] for k in list(lv)[:6]})
except Exception as e:                                    # noqa: BLE001
    print("[metrics] ERR", repr(e)[:90])

try:
    h = json.loads(urllib.request.urlopen("http://127.0.0.1:8090/health", timeout=5).read().decode())
    print("[health] ", {k: h.get(k) for k in ("status", "loaded", "max_context")})
except Exception as e:                                    # noqa: BLE001
    print("[health]  ERR", repr(e)[:80])

print("[配置]   md5", sh("md5sum " + CFG).split()[0])

if PROBE:
    # 探针：decode 128 tok（缓存命中） + TTFT（全新 prompt）
    def ask(text, mt):
        body = {"messages": [{"role": "user", "content": text}], "max_tokens": mt,
                "temperature": 0, "seed": 3}
        req = urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions",
                                     data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        t0 = time.time()
        r = urllib.request.urlopen(req, timeout=300)
        j = json.load(r)
        return time.time() - t0, (j.get("usage") or {}).get("completion_tokens")

    ask("预热：数三个数。", 64)
    w1, n1 = ask("请用一段话描写秋天。", 128)
    w2, n2 = ask("探针编号%d：请只回答一个字。" % int(time.time()), 1)
    print("[探针]   decode 128 tok: %.2f s → %.1f tok/s    TTFT(新prompt): %.0f ms"
          % (w1, (n1 or 0) / w1, w2 * 1000))
