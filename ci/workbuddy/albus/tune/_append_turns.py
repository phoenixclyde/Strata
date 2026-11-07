# 追加式多轮（真实对话形态）：每轮 prompt 是上一轮 prompt 的严格前缀。
# 与 w778_mt.py 的区别：那个是「分支」（共享 base、结尾指令不同），整段 checkpoint 本来就不是前缀。
import json, time, urllib.request, sys

URL = "http://127.0.0.1:8090"
MODEL = "qwen3.8-flash-next-ud-iq4_xs-abliterated"
PARAS = [
    "预填阶段的时间主要花在专家权重的换入与计算上，显存只能容纳其中一部分，其余由处理器承担。",
    "缓存命中率随上下文长度变化，短请求与长请求的路由分布不同，因此需要分档测量而不是合并统计。",
    "测量时必须确保没有复用，否则读入的 token 数会小于实际提示长度，吞吐会被高估。",
    "解码阶段由显卡承担主要计算，处理器占用很低，这与预填阶段的表现正好相反。",
]


def post(body, timeout=900):
    r = urllib.request.Request(URL + "/v1/chat/completions", data=json.dumps(body).encode(),
                               headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=timeout) as f:
        return json.loads(f.read().decode())


def last():
    with urllib.request.urlopen(URL + "/metrics", timeout=10) as f:
        d = json.loads(f.read().decode())
    return d["requests"][0], d.get("conversation_cache") or {}


def build(nonce, npar):
    head = "【会话标记 %s】\n" % nonce
    body = "".join(PARAS[i % len(PARAS)] for i in range(npar))
    return head + body


if __name__ == "__main__":
    nonce = sys.argv[1]
    npar = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    ctx = build(nonce, npar)
    for turn in range(1, 4):
        ctx = ctx + "\n问%d：这一轮请只回答一句确认，不要展开。" % turn
        t0 = time.time()
        try:
            d = post({"model": MODEL, "messages": [{"role": "user", "content": ctx}],
                      "max_tokens": 48, "temperature": 0})
            ans = d["choices"][0]["message"]["content"] or ""
        except Exception as e:
            print("turn%d ERROR %r" % (turn, e), flush=True)
            break
        r, cc = last()
        print("turn%d ptok=%s read=%s reused=%s prompt_ms=%s wall=%.1fs | cc parked=%s bytes=%s reused_tok=%s | ans=%r"
              % (turn, r.get("prompt_tokens"), r.get("prompt_read"), r.get("reused"), r.get("prompt_ms"),
                 time.time() - t0, cc.get("parked"), cc.get("bytes"), cc.get("reused_tokens"), (ans[:24] or "(empty)")),
              flush=True)
        ctx = ctx + "\n答%d：" % turn + ans
