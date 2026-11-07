#!/usr/bin/env python3
# W798b decode 基准 v2：
#   v1 的两个缺陷已修
#   (1) 每轮追加的问题**各不相同**（v1 都是"数数字"，draft 接受率随历史单调上升 => r1 4579 -> r6 3198，27% 假趋势）
#   (2) 打印 r3-r6 每一轮，便于"同轮次跨臂比较"；MEDIAN 只用 r4-r6
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
# 6 个互不相同的问题：内容形态不同 => draft 接受率不会随历史单调变化
ASKS = [
    "请逐行列出从 1 到 200 的数字，每行一个，不要解释。",
    "请用五段话解释什么是内存带宽，每段四到五句，不要列点。",
    "请写一个关于秋天的短故事，大约二百字，不要对话。",
    "请把下面这句话扩写成二百字：测量需要控制变量。",
    "请列举十个常见的测量误差来源，每条一句说明，不要编号之外的格式。",
    "请描述一次你想象中的深海旅行，二百字左右，不要重复用词。",
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
    txt = "".join(PARAS) * 6 + "【W798b 校准】"
    post({"model": MODEL, "messages": [{"role": "user", "content": txt}], "max_tokens": 1, "temperature": 0})
    lr = last_req()
    cpt = len(txt) / max(1, lr.get("prompt_tokens", 1))

    need = int(8000 * cpt)
    out, i = ["【W798b 基准】\n"], 0
    while sum(len(x) for x in out) < need:
        out.append(PARAS[i % len(PARAS)]); i += 1
    msgs = [{"role": "user", "content": "".join(out)}]
    d, wall = post({"model": MODEL, "messages": msgs, "max_tokens": 256, "temperature": 0})
    msgs = msgs + [{"role": "assistant", "content": (d["choices"][0]["message"].get("content") or "")}]
    lr = last_req()
    print("build: prompt_tok=%s prompt_ms=%s" % (lr.get("prompt_tokens"), lr.get("prompt_ms")))

    dms, dts = [], []
    for rd in range(1, 7):
        msgs = msgs + [{"role": "user", "content": ASKS[rd - 1]}]
        d, wall = post({"model": MODEL, "messages": msgs, "max_tokens": 256, "temperature": 0})
        lr = last_req()
        dm = lr.get("decode_ms") or 0
        dt = lr.get("decode_tok_s") or 0
        print("  r%d prompt_ms=%7.1f decode_ms=%7.1f decode_tok_s=%6.2f dur=%.2f"
              % (rd, lr.get("prompt_ms") or 0, dm, dt, wall))
        if rd >= 4:
            dms.append(dm); dts.append(dt)
        msgs = msgs + [{"role": "assistant", "content": (d["choices"][0]["message"].get("content") or "")}]
    if dms:
        print("MEDIAN decode_ms=%.1f decode_tok_s=%.2f  (r4-r6, 极差 %.1f%%)"
              % (statistics.median(dms), statistics.median(dts), (max(dms) / min(dms) - 1) * 100))


if __name__ == "__main__":
    main()
