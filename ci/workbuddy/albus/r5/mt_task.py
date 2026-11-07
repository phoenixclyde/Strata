# -*- coding: utf-8 -*-
"""W804 任务级门客户端：12 道可判分短提示任务，greedy，判「答对数」。

为什么需要这一层：W803 的 KL 只证明「分布没系统性移动」，证明不了「有没有变笨」。
上游对这个开关也只有速度（#3923）与一次 22/22 的质量套件（#1282 里 @did-technomancer 报的），
没有可比数字；本件给本卡自己的数字。

用法: mt_task.py <port> <tag> <out.json> <corpus.json> <max_tokens>
"""
import json, re, sys, time, urllib.request

PORT, TAG, OUT, CORPUS, MAXT = int(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5])
doc = json.load(open(CORPUS, encoding="utf-8"))
ANS = re.compile(r"ANSWER:\s*([^\s\n]+)", re.I)
# 下面两条都是为了把输出压到 6-9 个 token：默认思考会把 300 token 全花在枚举记录上（实测 finish=length）
#   (1) reasoning_effort=none（上游 #3923 的测法同样用它）
#   (2) 结尾硬性禁止枚举/解释，只允许一行 ANSWER:
SUFFIX = ("\n\nRules: do not enumerate the records, do not explain your steps. "
          "Reply with exactly one line and nothing else: ANSWER: <value>")


def ask(prompt):
    body = {"model": "default-big", "messages": [{"role": "user", "content": prompt + SUFFIX}],
            "max_tokens": MAXT, "temperature": 0.0, "reasoning_effort": "none"}
    req = urllib.request.Request("http://127.0.0.1:%d/v1/chat/completions" % PORT,
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=1800) as r:
            j = json.loads(r.read())
        txt = (j["choices"][0]["message"].get("content") or "")
        u = j.get("usage", {}) or {}
        return {"ok": True, "text": txt, "usage": u,
                "finish": j["choices"][0].get("finish_reason"),
                "wall_s": round(time.time() - t0, 2)}
    except Exception as e:
        return {"ok": False, "error": str(e), "wall_s": round(time.time() - t0, 2)}


res, n_ok = [], 0
for t in doc["tasks"]:
    r = ask(t["prompt"])
    r.update({"id": t["id"], "kind": t["kind"], "expect": t["expect"],
              "prompt_tokens": (r.get("usage") or {}).get("prompt_tokens")})
    m = ANS.findall(r.get("text") or "")
    r["got"] = m[-1].strip(" .,;:") if m else None
    r["correct"] = (r["got"] == t["expect"])
    n_ok += 1 if r["correct"] else 0
    res.append(r)
    print("  %s kind=%d expect=%-6s got=%-8s %s  finish=%s ptok=%s wall=%.1fs"
          % (t["id"], t["kind"], t["expect"], r["got"], "OK " if r["correct"] else "MISS",
             r.get("finish"), r.get("prompt_tokens"), r["wall_s"]), flush=True)
    time.sleep(0.5)

print("  SCORE %d/%d" % (n_ok, len(doc["tasks"])), flush=True)
json.dump({"tag": TAG, "max_tokens": MAXT, "score": n_ok, "n": len(doc["tasks"]), "results": res},
          open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("TASK_DONE " + TAG, flush=True)
