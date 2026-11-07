# -*- coding: utf-8 -*-
"""W804 读长扫描：单发 fresh prompt（无前缀复用），把 read 做成一条曲线。

用途有两个：
  1) P129 —— `STRATA_PREFILL_CPU_SHARE_MAX` 把 share 的作用域从 <1024 扩到 <3072，
     在 1024-3072 这一段是本卡从未测过的区间；
  2) 重新做相位账 —— W800 那张 `wait copy 754 ms` 的图是在 `share=0` 下量的，
     现在生产是 `auto`，那张图已经不代表现状。

每个尺寸发 3 次（每次换一段文本，避免命中对话缓存），只用 max_tokens=1 把 prompt 时间单独拿出来。
真值以引擎日志的 `prompt N tokens = ... read in T ms` 为准，客户端只记录墙钟。

用法: mt_read.py <port> <tag> <out.json> <sizes,逗号分隔> <reps> <pool.json> [START] [WARM]
      START = 语料池的起始下标（默认 0）。单发多请求时要换一个起点，否则每次都是同一段前缀
      => 会话缓存会命中前缀，`reused` 非 0，量的就不是全量 prefill 了。
      WARM  = 预热轮数（默认 2，W825/AUDIT11 加）。**每个新容器必须 >=2**：首请求带约 1.0 s 冷启动，
              不预热会把冷启动记进第一档。旧数据（W804/W810/W822/W824）都是 0，读它们时要记得这一条。
"""
import hashlib, json, sys, time, urllib.request

PORT, TAG, OUT = int(sys.argv[1]), sys.argv[2], sys.argv[3]
SIZES = [int(x) for x in sys.argv[4].split(",")]
REPS = int(sys.argv[5])
POOL = json.load(open(sys.argv[6], encoding="utf-8"))
CPT = 3.5          # 实测 chars/token（docs 散文，见 W803 §2）
cur = int(sys.argv[7]) if len(sys.argv) > 7 else 0
# W825/AUDIT11: 预热轮数。上游 tools/calibrate.py 的 warm_up(rounds=2) 同款。
# 首请求带约 1.0 s 冷启动（原始件 w816_det 的 TR 行：1018.3 ms → 167.7 → 稳态 57-65 ms），
# 不预热会把冷启动记进第一档，并让短档方差（4.6%）远大于长档（0.1%）—— 这两件事同源。
WARM = int(sys.argv[8]) if len(sys.argv) > 8 else 2


def take(chars):
    global cur
    out, n = [], 0
    while n < chars:
        out.append(POOL[cur % len(POOL)]); n += len(POOL[cur % len(POOL)]) + 1; cur += 1
    return " ".join(out)


def post(text):
    body = {"model": "default-big", "messages": [{"role": "user", "content": text}],
            "max_tokens": 1, "temperature": 0.0}
    req = urllib.request.Request("http://127.0.0.1:%d/v1/chat/completions" % PORT,
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=1800) as r:
            j = json.loads(r.read())
        u = j.get("usage", {}) or {}
        return {"ok": True, "prompt_tokens": u.get("prompt_tokens"),
                "wall_s": round(time.time() - t0, 2)}
    except Exception as e:
        return {"ok": False, "error": str(e), "wall_s": round(time.time() - t0, 2)}


# --- W825/AUDIT11: 预热，把冷启动挡在正式测量之外 ---
# `take()` 会推进 cur，所以预热用的是另一段文本，不会让正式测量命中 prompt 缓存
# （命中会得到 0.38 s / 6900 tok/s 这种假值 —— 本轮实测到过）。
warm = []
for _i in range(WARM):
    _w = post(take(int(min(SIZES) * CPT)))
    warm.append(_w.get("wall_s"))
    print("  warm%d wall=%.2fs ok=%s" % (_i, _w.get("wall_s") or 0, _w.get("ok")))

res = []
for rep in range(REPS):
    for sz in SIZES:
        txt = take(int(sz * CPT))
        rec = {"rep": rep, "target": sz, "chars": len(txt),
               "sha16": hashlib.sha256(txt.encode()).hexdigest()[:16]}
        rec.update(post(txt))
        res.append(rec)
        print("  rep%d target=%-5d chars=%-6d prompt_tokens=%-6s wall=%.2fs %s"
              % (rep, sz, len(txt), rec.get("prompt_tokens"), rec["wall_s"],
                 rec.get("error") or ""), flush=True)
        time.sleep(1)

json.dump({"tag": TAG, "sizes": SIZES, "reps": REPS, "warmup": WARM, "warm_wall": warm,
           "results": res},
          open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("READ_DONE " + TAG, flush=True)
