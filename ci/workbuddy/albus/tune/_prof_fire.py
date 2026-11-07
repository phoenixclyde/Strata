# 8091 端口上的 profile 触发请求：约 2.8K prompt + 300 输出，够产生近百个 decode 窗口。
import json, urllib.request

URL = "http://127.0.0.1:8091/v1/chat/completions"
MODEL = "qwen3.8-flash-next-ud-iq4_xs-abliterated"
PARAS = [
    "预填阶段的时间主要花在专家权重的换入与计算上，显存只能容纳其中一部分，其余由处理器承担。",
    "缓存命中率随上下文长度变化，短请求与长请求的路由分布不同，因此需要分档测量而不是合并统计。",
    "测量时必须确保没有复用，否则读入的 token 数会小于实际提示长度，吞吐会被高估。",
    "解码阶段由显卡承担主要计算，处理器占用很低，这与预填阶段的表现正好相反。",
]


def post_retry(body, tries=8, gap=6, timeout=600):
    import time
    last = None
    for i in range(tries):
        try:
            return post(body, timeout)
        except Exception as e:
            last = e
            print("  retry %d: %r" % (i + 1, e))
            time.sleep(gap)
    raise last


def post(body, timeout=600):
    r = urllib.request.Request(URL, data=json.dumps(body).encode(),
                               headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=timeout) as f:
        return json.loads(f.read().decode())


if __name__ == "__main__":
    # 预热（触发一次 prefill，让后面的 profile 只覆盖稳态 decode）
    try:
        post_retry({"model": MODEL, "messages": [{"role": "user", "content": "预热"}], "max_tokens": 4, "temperature": 0})
        print("warmup ok")
    except Exception as e:
        print("warmup ERR", repr(e))

    body_text = "【profile 用】\n" + "".join(PARAS[i % len(PARAS)] for i in range(300))
    d = post_retry({"model": MODEL, "messages": [{"role": "user", "content": body_text + "\n只用一句确认。"}],
              "max_tokens": 300, "temperature": 0})
    u = d.get("usage") or {}
    print("profiled request: prompt=%s completion=%s" % (u.get("prompt_tokens"), u.get("completion_tokens")))
