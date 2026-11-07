# 推到 166 上执行：三档冷读基线（S/M/L），口径 = 唯一 nonce 强制整段重读
import json, time, urllib.request, statistics, sys

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


def post(path, body, timeout=900):
    req = urllib.request.Request(URL + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read().decode())
    return d, time.time() - t0


def metrics():
    with urllib.request.urlopen(URL + "/metrics", timeout=10) as r:
        return json.loads(r.read().decode())


def last_req():
    m = metrics()
    rs = m.get("requests") or []
    return rs[0] if rs else None


def build(nonce, target_tokens, cpt):
    head = "【测量标记 %s】\n" % nonce
    tail = "\n\n回答要求：请逐行列出从 1 到 150 的数字，每行一个，不要解释，不要总结。"
    need = max(0, int(target_tokens * cpt) - len(head) - len(tail))
    out = [head]
    i = 0
    while sum(len(x) for x in out) < need:
        out.append(PARAS[i % len(PARAS)])
        i += 1
    return "".join(out) + tail


def probe_cpt():
    """用固定长度探针校准 字符/token"""
    txt = "".join(PARAS) * 6 + "【探针 probe-calib】"
    r, dt = post("/v1/chat/completions", {"model": MODEL, "messages": [{"role": "user", "content": txt}],
                                          "max_tokens": 1, "temperature": 0})
    lr = last_req()
    pt = lr["prompt_tokens"]
    return len(txt) / pt


def run_tier(tag, target, n, max_tokens):
    cpt = probe_cpt()
    rows = []
    print("  [%s] cpt=%.2f chars/token" % (tag, cpt), flush=True)
    for i in range(n):
        nonce = "w776%s%s%02d" % (tag, str(int(time.time()))[-6:], i + 1)   # 时间戳：同一档第二次调用不得复用上一次的 prompt
        txt = build(nonce, target, cpt)
        t0 = time.time()
        try:
            r, dt = post("/v1/chat/completions", {"model": MODEL, "messages": [{"role": "user", "content": txt}],
                                                  "max_tokens": max_tokens, "temperature": 0})
        except Exception as ex:
            print("  [%s] run%d ERROR %r" % (tag, i + 1, ex), flush=True)
            continue
        lr = last_req()
        pt = lr.get("prompt_tokens"); reused = lr.get("reused"); pms = lr.get("prompt_ms")
        dts = lr.get("decode_tok_s"); ot = lr.get("output_tokens")
        pts = (pt / (pms / 1000.0)) if pms else 0
        rows.append(dict(run=i + 1, ptok=pt, reused=reused, pms=pms, pts=pts, dts=dts, otok=ot, wall=dt))
        print("  [%s] run%d ptok=%s reused=%s prompt_ms=%.0f prompt_tps=%.1f decode_tps=%s out=%s wall=%.1fs"
              % (tag, i + 1, pt, reused, pms or -1, pts, dts, ot, dt), flush=True)
    if rows:
        ok = [r for r in rows if r["reused"] == 0]
        print("  [%s] n=%d reused0=%d | prompt_tps median=%.1f  decode_tps median=%s"
              % (tag, len(rows), len(ok),
                 statistics.median([r["pts"] for r in ok]) if ok else -1,
                 ("%.1f" % statistics.median([r["dts"] for r in ok if r["dts"]])) if ok and any(r["dts"] for r in ok) else "-"),
              flush=True)


if __name__ == "__main__":
    tag = sys.argv[1]
    which = {"S": (2900, 5, 320), "M": (23000, 5, 320), "L": (105000, 2, 32)}[tag]
    if len(sys.argv) > 2:
        which = (which[0], int(sys.argv[2]), which[2])
    run_tier(tag, *which)
