#!/usr/bin/env python3
# W798 阶段 A：多轮基线（规则 K —— 先量清 decode 在真实用法下占端到端多少）
#
# 动机：单轮 M 档 decode 只占 15%、L 档 0.5%，但**多轮对话时 prompt 大部分复用**，
# 第 2 轮之后 decode 才是主项。上游 10 个 decode 开关的收益（+1.8% / +2.3% / +6.7%）都是
# "decode 单步"口径，必须先知道 decode 占端到端多少，否则又是规则 K 的错误。
#
# 做法：同一会话（相同 messages 前缀 + 追加）连发 6 轮，每轮 max_tokens=256，
# 记录 prompt_tokens / reused / prompt_ms / decode_tps / wall，算每一轮的 decode 时间占比。
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


def long_text(target_tokens, cpt):
    need = max(0, int(target_tokens * cpt))
    out = ["【多轮基线 W798】\n"]
    i = 0
    while sum(len(x) for x in out) < need:
        out.append(PARAS[i % len(PARAS)])
        i += 1
    return "".join(out)


def probe_cpt():
    txt = "".join(PARAS) * 6 + "【探针 W798】"
    r, _ = post({"model": MODEL, "messages": [{"role": "user", "content": txt}], "max_tokens": 1, "temperature": 0})
    lr = last_req()
    return len(txt) / max(1, lr.get("prompt_tokens", 1))


def main():
    cpt = probe_cpt()
    print("cpt=%.3f chars/token" % cpt, flush=True)
    text = long_text(20000, cpt)
    msgs = [{"role": "user", "content": text}]
    print("%-3s %9s %8s %8s %9s %9s %8s %8s" % ("rd", "prompt_tok", "reused", "prompt_ms", "decode_tps",
                                                "out_tok", "wall_s", "dec_frac"), flush=True)
    fracs = []
    for rd in range(1, 7):
        body = {"model": MODEL, "messages": msgs, "max_tokens": 256, "temperature": 0}
        d, wall = post(body)
        lr = last_req()
        pt = lr.get("prompt_tokens", 0)
        reused = lr.get("reused", 0)
        pms = lr.get("prompt_ms", 0)
        dtps = lr.get("decode_tps", 0) or 0
        out = (d.get("usage") or {}).get("completion_tokens", 0)
        dec_s = (out / dtps) if dtps else 0
        frac = dec_s / wall if wall else 0
        if rd >= 3:
            fracs.append(frac)
        print("%-3d %9d %8d %8d %9.2f %9d %8.2f %7.1f%%" % (rd, pt, reused, pms, dtps, out, wall, frac * 100), flush=True)
        reply = (d["choices"][0]["message"].get("content") or "")
        msgs = msgs + [{"role": "assistant", "content": reply},
                       {"role": "user", "content": "请从 1 数到 200，每行一个数字，不要解释。"}]
    if fracs:
        print("\n第 3-6 轮 decode 时间占端到端: 中位 %.1f%%  区间 %.1f-%.1f%%"
              % (statistics.median(fracs) * 100, min(fracs) * 100, max(fracs) * 100), flush=True)


if __name__ == "__main__":
    main()
