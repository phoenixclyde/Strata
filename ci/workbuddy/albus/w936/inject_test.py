#!/usr/bin/env python3
"""W936 / R77 test: STRATA_INJECT_FATAL=2 must end the engine on the 2nd decode window.
Request 2 should get a 503 (retryable), the server should restart the engine, and request 3 should answer.
ASCII only."""
import json, time, urllib.request, urllib.error

URL = "http://127.0.0.1:8090/v1/chat/completions"
BODY = {
    "model": "x",
    "messages": [{"role": "user", "content": "Say the single word: ok"}],
    "max_tokens": 8,
    "temperature": 0,
}


def post(tag):
    data = json.dumps(BODY).encode()
    req = urllib.request.Request(URL, data=data, headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            raw = r.read()
            dt = time.time() - t0
            try:
                j = json.loads(raw)
                msg = j.get("choices", [{}])[0].get("message", {}) or {}
                txt = (msg.get("content") or msg.get("reasoning_content") or "")[:40]
                usage = j.get("usage", {})
                print("%-10s http=%d  %.1fs  text=%r  tokens=%s" % (tag, r.status, dt, txt, usage.get("completion_tokens")))
            except Exception:
                print("%-10s http=%d  %.1fs  (unparsed) %r" % (tag, r.status, dt, raw[:120]))
            return r.status
    except urllib.error.HTTPError as e:
        raw = e.read()
        dt = time.time() - t0
        print("%-10s http=%d  %.1fs  BODY=%r" % (tag, e.code, dt, raw[:300]))
        return e.code
    except Exception as e:
        dt = time.time() - t0
        print("%-10s EXC %.1fs  %s: %s" % (tag, dt, type(e).__name__, str(e)[:160]))
        return None


print("=== step 1: 第 1 个请求（第 1 个 decode 窗口，不应触发）===")
post("req1")

print()
print("=== step 2: 第 2 个请求（第 2 个窗口，应触发 fatal）===")
post("req2")

print()
print("=== step 3: 等引擎重启并测第 3 个请求 ===")
t0 = time.time()
ok = False
for i in range(60):
    st = None
    try:
        r = urllib.request.urlopen("http://127.0.0.1:8090/health", timeout=3)
        if b'"ok"' in r.read():
            st = "ok"
    except Exception:
        st = None
    if st == "ok":
        print("  health ok after %.0fs" % (time.time() - t0))
        ok = True
        break
    time.sleep(2)
if not ok:
    print("  health 未恢复（%.0fs）" % (time.time() - t0))

post("req3")
print()
print("=== step 4: 后续请求（标志文件已在，不应再注入）===")
post("req4")
