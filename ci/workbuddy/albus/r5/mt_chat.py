#!/usr/bin/env python3
# W801：真实多轮 chat 口径的 bench —— 8K 会话，4 轮（read 目标 80/280/80/280），每次生成 64 token
# 输出每轮 prompt_ms(=TTFT 的服务器侧)、decode_ms、decode_tok_s、wall
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
    return d, time.time() - t0

def last():
    with urllib.request.urlopen(URL + "/metrics", timeout=10) as r:
        m = json.loads(r.read().decode())
    rs = m.get("requests") or []
    return rs[0] if rs else {}

txt = "".join(PARAS) * 6 + "【W801 chat 校准】"
post({"model": MODEL, "messages": [{"role": "user", "content": txt}], "max_tokens": 1, "temperature": 0})
cpt = len(txt) / max(1, last().get("prompt_tokens", 1))

need = int(8000 * cpt)
base, i = ["【W801 chat 底】\n"], 0
while sum(len(x) for x in base) < need:
    base.append(PARAS[i % len(PARAS)]); i += 1
msgs = [{"role": "user", "content": "".join(base)}]
d, w = post({"model": MODEL, "messages": msgs, "max_tokens": 16, "temperature": 0})
lr = last()
print("BUILD wall=%.2f reused=%s read=%s prompt_ms=%s" % (w, lr.get("reused"), lr.get("prompt_read"), lr.get("prompt_ms")), flush=True)
msgs = msgs + [{"role": "assistant", "content": (d["choices"][0]["message"].get("content") or "略")}]

TARGETS = [int(x) for x in (sys.argv[1].split(",") if len(sys.argv) > 1 else ["80", "280", "80", "280"])]
GEN = int(sys.argv[2]) if len(sys.argv) > 2 else 64
for t, sz in enumerate(TARGETS):
    ask, j = ["第%d问，" % t], 0
    while sum(len(x) for x in ask) < int(sz * cpt):
        ask.append(PARAS[j % len(PARAS)]); j += 1
    d, w = post({"model": MODEL, "messages": msgs + [{"role": "user", "content": "".join(ask)}],
                 "max_tokens": GEN, "temperature": 0})
    lr = last()
    print("T%d ask=%-4d read=%-5s reused=%-5s prompt_ms=%8.1f decode_ms=%8.1f tok_s=%5.1f wall=%5.2f" % (
        t, sz, lr.get("prompt_read"), lr.get("reused"), lr.get("prompt_ms") or 0,
        lr.get("decode_ms") or 0, lr.get("decode_tok_s") or 0, w), flush=True)
    msgs = msgs + [{"role": "assistant", "content": "（略）"}]
print("DONE", flush=True)
