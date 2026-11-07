#!/usr/bin/env python3
# W798 的 decode 基准：8K prompt 建会话 -> 6 次追加（256 tokens）-> 打印每轮与第 4-6 轮中位
# 判据看 decode_ms（tokens 固定 256，ms 越小越快）与 decode_tok_s。
import json, time, urllib.request, statistics

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


def last_req():
    with urllib.request.urlopen(URL + "/metrics", timeout=10) as r:
        m = json.loads(r.read().decode())
    rs = m.get("requests") or []
    return rs[0] if rs else {}


def main():
    # 校准 chars/token
    txt = "".join(PARAS) * 6 + "【W798 校准】"
    post({"model": MODEL, "messages": [{"role": "user", "content": txt}], "max_tokens": 1, "temperature": 0})
    lr = last_req()
    cpt = len(txt) / max(1, lr.get("prompt_tokens", 1))

    need = int(8000 * cpt)
    out, i = ["【W798 decode 基准】\n"], 0
    while sum(len(x) for x in out) < need:
        out.append(PARAS[i % len(PARAS)]); i += 1
    msgs = [{"role": "user", "content": "".join(out)}]

    # 建会话（这一轮不计）
    d, wall = post({"model": MODEL, "messages": msgs, "max_tokens": 256, "temperature": 0})
    msgs = msgs + [{"role": "assistant", "content": (d["choices"][0]["message"].get("content") or "")},
                   {"role": "user", "content": "请从 1 数到 200，每行一个数字，不要解释。"}]
    lr = last_req()
    print("build: prompt_tok=%s prompt_ms=%s wall=%.2f" % (lr.get("prompt_tokens"), lr.get("prompt_ms"), wall))

    dms, dts, durs = [], [], []
    for rd in range(1, 7):
        d, wall = post({"model": MODEL, "messages": msgs, "max_tokens": 256, "temperature": 0})
        lr = last_req()
        pms = lr.get("prompt_ms") or 0
        dm = lr.get("decode_ms") or 0
        dt = lr.get("decode_tok_s") or 0
        print("  r%d prompt_ms=%7.1f decode_ms=%7.1f decode_tok_s=%6.2f dur=%.2f dec_frac=%.1f%%"
              % (rd, pms, dm, dt, wall, 100.0 * dm / (wall * 1000) if wall else 0))
        if rd >= 4:
            dms.append(dm); dts.append(dt); durs.append(wall)
        reply = (d["choices"][0]["message"].get("content") or "")
        msgs = msgs + [{"role": "assistant", "content": reply},
                       {"role": "user", "content": "再数一遍，从 1 到 200，每行一个数字。"}]
    if dms:
        print("MEDIAN decode_ms=%.1f decode_tok_s=%.2f dur=%.2f  (n=%d, 极差 %.1f%%)"
              % (statistics.median(dms), statistics.median(dts), statistics.median(durs), len(dms),
                 (max(dms) / min(dms) - 1) * 100))


if __name__ == "__main__":
    main()
