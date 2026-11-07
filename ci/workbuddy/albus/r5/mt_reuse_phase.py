#!/usr/bin/env python3
# W799：多轮复用（reused）到底把时间花在哪 —— 开 STRATA_PREFILL_TIMING 拿相位账
# 第 1 轮冷（reused=0）作参照，第 2/3 轮 reused~99.8%
import json, time, urllib.request

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


txt = "".join(PARAS) * 6 + "【W799 校准】"
post({"model": MODEL, "messages": [{"role": "user", "content": txt}], "max_tokens": 1, "temperature": 0})
cpt = len(txt) / max(1, last().get("prompt_tokens", 1))
need = int(8000 * cpt)
out, i = ["【W799 复用相位】\n"], 0
while sum(len(x) for x in out) < need:
    out.append(PARAS[i % len(PARAS)]); i += 1
msgs = [{"role": "user", "content": "".join(out)}]
for rd in range(1, 4):
    if rd > 1:
        msgs = msgs + [{"role": "user", "content": "请从 1 数到 200，每行一个数字，不要解释。"}]
    d, wall = post({"model": MODEL, "messages": msgs, "max_tokens": 256, "temperature": 0})
    lr = last()
    print("R%d prompt_tok=%s reused=%s read=%s prompt_ms=%s decode_ms=%s dur=%.2f"
          % (rd, lr.get("prompt_tokens"), lr.get("reused"), lr.get("prompt_read"),
             lr.get("prompt_ms"), lr.get("decode_ms"), wall))
    msgs = msgs + [{"role": "assistant", "content": (d["choices"][0]["message"].get("content") or "")}]
