
import json, time, urllib.request
doc = json.load(open("task_smoke.json", encoding="utf-8"))
SUFFIX = ("\n\nRules: do not enumerate the records, do not explain your steps. "
          "Reply with exactly one line and nothing else: ANSWER: <value>")
for i, t in enumerate(doc["tasks"]):
    for mt in (60, 120):
        body = {"model": "default-big",
                "messages": [{"role": "user", "content": t["prompt"] + SUFFIX}],
                "max_tokens": mt, "temperature": 0.0, "reasoning_effort": "none"}
        req = urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions",
                                     data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=600) as r:
            j = json.loads(r.read())
        ch = j["choices"][0]
        print("t0%d mt=%-3d expect=%-6s finish=%-6s ctok=%-3d %.1fs  text=%r"
              % (i, mt, t["expect"], ch.get("finish_reason"), j["usage"]["completion_tokens"],
                 time.time()-t0, (ch["message"].get("content") or "")[:80]))
