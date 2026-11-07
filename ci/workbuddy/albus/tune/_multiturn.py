# 推到 166 执行：多轮复用测试（第 2 轮与第 1 轮共享前缀，只有结尾不同）
import json, time, urllib.request, sys

URL = "http://127.0.0.1:8090"
MODEL = "qwen3.8-flash-next-ud-iq4_xs-abliterated"
PARAS = [
    "预填阶段的时间主要花在专家权重的换入与计算上，显存只能容纳其中一部分，其余由处理器承担。",
    "缓存命中率随上下文长度变化，短请求与长请求的路由分布不同，因此需要分档测量而不是合并统计。",
    "测量时必须确保没有复用，否则读入的 token 数会小于实际提示长度，吞吐会被高估。",
    "解码阶段由显卡承担主要计算，处理器占用很低，这与预填阶段的表现正好相反。",
]


def post(body, timeout=600):
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
    base = build(nonce, npar)
    turns = [base + "\n请只回答：第一轮。",
             base + "\n请只回答：第二轮。",
             base + "\n请只回答：第三轮。"]
    for i, txt in enumerate(turns, 1):
        t0 = time.time()
        try:
            post({"model": MODEL, "messages": [{"role": "user", "content": txt}],
                  "max_tokens": 64, "temperature": 0})
        except Exception as e:
            print("turn%d ERROR %r" % (i, e)); break
        r, cc = last()
        print("turn%d ptok=%s read=%s reused=%s prompt_ms=%s wall=%.1fs | cc parked=%s slots=%s bytes=%s reused_tok=%s"
              % (i, r.get("prompt_tokens"), r.get("prompt_read"), r.get("reused"), r.get("prompt_ms"),
                 time.time() - t0, cc.get("parked"), cc.get("slots"), cc.get("bytes"), cc.get("reused_tokens")),
              flush=True)
