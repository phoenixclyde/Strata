#!/usr/bin/env python3
# W800e: decode 侧的 ROUTE_TAIL_SKIP A/B —— 两臂各 3 轮，每轮生成 96 token
# 判据：decode_tok_s（以及 drafts_accepted，因为 #1884 说 skip 会压低草稿接受率）
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

txt = "".join(PARAS) * 2 + "【W800e 校准】"
post({"model": MODEL, "messages": [{"role": "user", "content": txt}], "max_tokens": 1, "temperature": 0})
cpt = len(txt) / max(1, last().get("prompt_tokens", 1))

need = int(2000 * cpt)
base, i = ["【W800e 底】\n"], 0
while sum(len(x) for x in base) < need:
    base.append(PARAS[i % len(PARAS)]); i += 1
msgs = [{"role": "user", "content": "".join(base)}]
d, w = post({"model": MODEL, "messages": msgs, "max_tokens": 8, "temperature": 0})
lr = last()
print("BUILD wall=%.2f read=%s prompt_ms=%s" % (w, lr.get("prompt_read"), lr.get("prompt_ms")), flush=True)
msgs = msgs + [{"role": "assistant", "content": "（略）"}]

GEN = int(sys.argv[1]) if len(sys.argv) > 1 else 96
for t in range(3):
    body = msgs + [{"role": "user", "content": "请写一段关于第%d问的分析。" % t}]
    d, w = post({"model": MODEL, "messages": body, "max_tokens": GEN, "temperature": 0})
    lr = last()
    print("TURN%d wall=%.2f prompt_ms=%s decode_ms=%s tok_s=%s gen=%s drafts=%s/%s reused=%s" % (
        t, w, lr.get("prompt_ms"), lr.get("decode_ms"), lr.get("decode_tok_s"), lr.get("output_tokens"),
        lr.get("drafts_accepted"), lr.get("drafts_offered"), lr.get("reused")), flush=True)
    msgs = msgs + [{"role": "assistant", "content": "（略）"}]
print("DONE", flush=True)
