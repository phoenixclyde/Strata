#!/usr/bin/env python3
# W802c：CPU share 采纳前的最小门 —— 无仪器复测 TTFT + 输出逐 token 一致 + M 不变
import json, time, urllib.request, sys, hashlib

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
TAG = sys.argv[1] if len(sys.argv) > 1 else "X"

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

# --- parity：固定问题、贪心、48 token，落盘正文用于跨臂逐字比对
Q = "用三句话说明为什么缓存命中率会随上下文变长而下降，最后给出一个具体数值例子。"
d, w = post({"model": MODEL, "messages": [{"role": "user", "content": Q}], "max_tokens": 48, "temperature": 0})
txt = d["choices"][0]["message"].get("content") or ""
h = hashlib.sha256(txt.encode()).hexdigest()[:16]
print("PARITY %s md5=%s len=%d finish=%s" % (TAG, h, len(txt), d["choices"][0].get("finish_reason")), flush=True)
open("/home/albus/strata166/data/w802_parity_%s.txt" % TAG, "w", encoding="utf-8").write(txt)

# --- chat bench（无仪器）
txt2 = "".join(PARAS) * 6 + "【W802c 校准】"
post({"model": MODEL, "messages": [{"role": "user", "content": txt2}], "max_tokens": 1, "temperature": 0})
cpt = len(txt2) / max(1, last().get("prompt_tokens", 1))
need = int(8000 * cpt)
base, i = ["【W802c 底】\n"], 0
while sum(len(x) for x in base) < need:
    base.append(PARAS[i % len(PARAS)]); i += 1
msgs = [{"role": "user", "content": "".join(base)}]
d, w = post({"model": MODEL, "messages": msgs, "max_tokens": 16, "temperature": 0})
lr = last()
print("BUILD wall=%.2f read=%s prompt_ms=%s" % (w, lr.get("prompt_read"), lr.get("prompt_ms")), flush=True)
msgs = msgs + [{"role": "assistant", "content": (d["choices"][0]["message"].get("content") or "略")}]
for t, sz in enumerate([80, 280, 80, 280]):
    ask, j = ["第%d问，" % t], 0
    while sum(len(x) for x in ask) < int(sz * cpt):
        ask.append(PARAS[j % len(PARAS)]); j += 1
    d, w = post({"model": MODEL, "messages": msgs + [{"role": "user", "content": "".join(ask)}],
                 "max_tokens": 64, "temperature": 0})
    lr = last()
    print("T%d ask=%-4d read=%-5s prompt_ms=%8.1f decode_ms=%8.1f tok_s=%5.1f wall=%5.2f" % (
        t, sz, lr.get("prompt_read"), lr.get("prompt_ms") or 0, lr.get("decode_ms") or 0,
        lr.get("decode_tok_s") or 0, w), flush=True)
    msgs = msgs + [{"role": "assistant", "content": "（略）"}]
print("DONE", flush=True)
