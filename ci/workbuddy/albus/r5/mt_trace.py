#!/usr/bin/env python3
# W800a: 请求级时间线探针 —— 3 轮固定会话，每轮 read~200 token。
# 客户端打点 T0/T1（与 docker logs -t 同一时钟），服务端开 STRATA_TRACE=1 出逐阶段行。
import json, time, urllib.request, sys

URL = "http://127.0.0.1:8090"
MODEL = "qwen3.8-flash-next-ud-iq4_xs-abliterated"
PARAS = [
    "预填阶段的时间主要花在专家权重的换入与计算上，显存只能容纳其中一部分，其余由处理器承担。",
    "缓存命中率随上下文长度变化，短请求与长请求的路由分布不同，因此需要分档测量而不是合并统计。",
    "测量时必须确保没有复用，否则读入的 token 数会小于实际提示长度，吞吐会被高估。",
    "每一轮加一个唯一标记，让服务端把它当成全新的对话，从而强制从头读取整段提示。",
    "解码阶段由显卡承担主要计算，处理器占用很低，这与预填阶段的表现正好相反。",
    "统计上取中位数而不是平均值，因为首轮往往带有冷启动开销，会把均值拉低。",
]

def post(body, timeout=900):
    req = urllib.request.Request(URL + "/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read().decode())
    return d, t0, time.time()

def last():
    with urllib.request.urlopen(URL + "/metrics", timeout=10) as r:
        m = json.loads(r.read().decode())
    rs = m.get("requests") or []
    return rs[0] if rs else {}

# 校准 token/字符
txt = "".join(PARAS) * 6 + "【W800a 校准】"
post({"model": MODEL, "messages": [{"role": "user", "content": txt}], "max_tokens": 1, "temperature": 0})
cpt = len(txt) / max(1, last().get("prompt_tokens", 1))

need = int(8000 * cpt)
base, i = ["【W800a 会话底】\n"], 0
while sum(len(x) for x in base) < need:
    base.append(PARAS[i % len(PARAS)]); i += 1
msgs = [{"role": "user", "content": "".join(base)}]
d, a, b = post({"model": MODEL, "messages": msgs, "max_tokens": 8, "temperature": 0})
lr = last()
print("BUILD t0=%.4f t1=%.4f reused=%s read=%s prompt_ms=%s" %
      (a, b, lr.get("reused"), lr.get("prompt_read"), lr.get("prompt_ms")), flush=True)
print("KEYS " + ",".join(sorted(lr.keys())), flush=True)
msgs = msgs + [{"role": "assistant", "content": (d["choices"][0]["message"].get("content") or "")}]

TURNS = int(sys.argv[1]) if len(sys.argv) > 1 else 3
README = int(sys.argv[2]) if len(sys.argv) > 2 else 200
for t in range(TURNS):
    ask, j = ["请根据上文回答第%d问：" % t], 0
    while sum(len(x) for x in ask) < int(README * cpt):
        ask.append(PARAS[j % len(PARAS)]); j += 1
    body = msgs + [{"role": "user", "content": "".join(ask)}]
    d, a, b = post({"model": MODEL, "messages": body, "max_tokens": 8, "temperature": 0})
    lr = last()
    print("TURN%d t0=%.4f t1=%.4f wall=%.3f reused=%s read=%s ptok=%s prompt_ms=%s" %
          (t, a, b, b - a, lr.get("reused"), lr.get("prompt_read"), lr.get("prompt_tokens"), lr.get("prompt_ms")),
          flush=True)
    msgs = msgs + [{"role": "assistant", "content": "（略）"}]
print("DONE", flush=True)
