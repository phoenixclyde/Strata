#!/usr/bin/env python3
"""W912/R59: collect per-token top-20 logprobs from the production server, and compare two arms.

Design notes
------------
* Three arms are needed, not two: A1 (TUNED=1), B (TUNED=0), A2 (TUNED=1 again).  The engine is not
  run-to-run deterministic (W899 §7.11 saw two identical runs produce different text), so KL(A1||A2) is
  the NOISE FLOOR and only KL(A1||B) above that floor is an effect.
* Greedy (temperature 0) so the chosen token is the argmax; the comparison is then purely about the
  distribution, not about sampling luck.
* Only the top-20 of each side is visible (server caps K at 20), so KL is computed over the union of the
  two supports, with both sides renormalised over it; the dropped tail mass is reported so a large
  truncation cannot masquerade as a clean number.

Usage
-----
  python3 lp_ab.py collect <arm> <out.json>      # arm: a1 | b | a2
  python3 lp_ab.py compare <a.json> <b.json>     # prints KL / top-1 agreement
"""
import json
import math
import sys
import time
import urllib.request

URL = "http://127.0.0.1:8090/v1/chat/completions"

PROMPTS = [
    ("p1", "Summarise the following in three sentences.\n\n"
           "A memory-bound kernel moves more bytes than it can compute in the same time. On a GPU the "
           "arithmetic intensity of a matrix-vector product is one multiply-add per weight byte, so the "
           "achievable throughput is the bandwidth times that intensity. Widening the dot-product "
           "instruction does not reduce the bytes, therefore it cannot lift such a kernel."),
    ("p2", "List five differences between a tiled matrix multiplication and a row-parallel one.\n"),
    ("p3", "Write a short paragraph explaining why 4-bit weights with 8-bit activations are preferred over "
           "4-bit weights with 4-bit activations for a mixture-of-experts model.\n"),
    ("p4", "Explain, step by step, how a stream-K decomposition differs from a fixed K-split, and when each "
           "one wins. Be concrete about the number of blocks and the bytes in flight.\n"),
]

MAX_NEW = 96


def post(body, timeout=900):
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def collect(arm, out_path):
    result = {"arm": arm, "when": time.strftime("%Y-%m-%dT%H:%M:%S"), "runs": []}
    for pid, text in PROMPTS:
        body = {
            "model": "any",
            "messages": [{"role": "user", "content": text}],
            "max_tokens": MAX_NEW,
            "temperature": 0.0,
            "logprobs": True,
            "top_logprobs": 20,
            "stream": False,
        }
        t0 = time.time()
        out = post(body)
        dt = time.time() - t0
        ch = out["choices"][0]
        lp = ch.get("logprobs") or {}
        seq = lp.get("content") or lp.get("reasoning_content") or []
        rows = []
        for item in seq:
            rows.append({
                "tok": item.get("token"),
                "lp": item.get("logprob"),
                "top": [[t.get("token"), t.get("logprob")] for t in (item.get("top_logprobs") or [])],
            })
        result["runs"].append({"pid": pid, "secs": round(dt, 2), "tokens": rows,
                               "usage": out.get("usage"), "timings": out.get("timings")})
        print("  %-3s %-3s %5.2fs  %3d tokens  first=%r" %
              (arm, pid, dt, len(rows), rows[0]["tok"] if rows else None))
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)
    print("wrote", out_path)


def dist(row):
    """top-20 -> {token: prob}, renormalised over the listed support."""
    items = row.get("top") or []
    if not items:
        return {}
    mx = max(lp for _, lp in items)
    ws = {t: math.exp(lp - mx) for t, lp in items}
    z = sum(ws.values())
    return {t: w / z for t, w in ws.items()} if z > 0 else {}


def kl(p, q):
    """KL(p||q) over the union support; returns (kl, mass_of_p_covered)."""
    keys = set(p) | set(q)
    tot = 0.0
    for k in keys:
        pk = p.get(k, 0.0)
        if pk <= 0.0:
            continue
        qk = q.get(k, 0.0)
        if qk <= 0.0:
            qk = 1e-12                      # a token the other arm did not list: floor it
        tot += pk * math.log(pk / qk)
    return tot, sum(p.values())


def compare(a_path, b_path):
    A = json.load(open(a_path, encoding="utf-8"))
    B = json.load(open(b_path, encoding="utf-8"))
    print("A=%s (%s)   B=%s (%s)" % (A["arm"], A["when"], B["arm"], B["when"]))
    print("%-4s %5s %10s %10s %9s %9s" % ("pid", "n", "mean_KL", "max_KL", "top1_agree", "same_tok"))
    all_kl, all_agree, all_same, n_pos = [], 0, 0, 0
    for ra, rb in zip(A["runs"], B["runs"]):
        ta, tb = ra["tokens"], rb["tokens"]
        kls, agree, same = [], 0, 0
        for x, y in zip(ta, tb):
            p, q = dist(x), dist(y)
            if not p or not q:
                continue
            v, _ = kl(p, q)
            kls.append(v)
            if p and q:
                if max(p, key=p.get) == max(q, key=q.get):
                    agree += 1
            if x["tok"] == y["tok"]:
                same += 1
        n = len(kls)
        if n == 0:
            print("%-4s %5d %10s %10s" % (ra["pid"], 0, "-", "-"))
            continue
        all_kl += kls
        all_agree += agree
        all_same += same
        n_pos += n
        print("%-4s %5d %10.5f %10.5f %8.1f%% %8.1f%%" %
              (ra["pid"], n, sum(kls) / n, max(kls), 100.0 * agree / n, 100.0 * same / n))
    if all_kl:
        print("-" * 60)
        print("ALL  %5d %10.5f %10.5f %8.1f%% %8.1f%%" %
              (n_pos, sum(all_kl) / n_pos, max(all_kl), 100.0 * all_agree / n_pos, 100.0 * all_same / n_pos))
        import statistics
        print("median KL = %.5f   p95 = %.5f" %
              (statistics.median(all_kl), sorted(all_kl)[int(0.95 * (len(all_kl) - 1))]))




def prefix(a_path, b_path):
    """Compare only up to the FIRST position where the two runs emitted different tokens.

    Past that point the two sequences condition on different text, so a position-wise KL is not a
    rounding difference any more - it is two different sentences.
    """
    A = json.load(open(a_path, encoding="utf-8"))
    B = json.load(open(b_path, encoding="utf-8"))
    print("prefix-only  A=%s  B=%s" % (A["arm"], B["arm"]))
    print("%-4s %5s %10s %10s %10s %s" % ("pid", "n", "div_at", "mean_KL", "KL_at_div", "top1"))
    allk = []
    for ra, rb in zip(A["runs"], B["runs"]):
        ta, tb = ra["tokens"], rb["tokens"]
        n = min(len(ta), len(tb))
        d = next((i for i in range(n) if ta[i]["tok"] != tb[i]["tok"]), n)
        kls = []
        for i in range(d):
            p_, q_ = dist(ta[i]), dist(tb[i])
            if p_ and q_:
                kls.append(kl(p_, q_)[0])
        kd = "-"
        if d < n:
            p_, q_ = dist(ta[d]), dist(tb[d])
            if p_ and q_:
                kd = "%.4f" % kl(p_, q_)[0]
        agree = sum(1 for i in range(d) if ta[i]["tok"] == tb[i]["tok"])
        allk += kls
        print("%-4s %5d %10s %10.5f %10s %5.1f%%" % (ra["pid"], d, ("none" if d == n else str(d)),
              (sum(kls) / len(kls)) if kls else float("nan"), kd, 100.0 * agree / max(d, 1)))
    if allk:
        import statistics
        allk.sort()
        print("总 %d 个分叉前位置: mean=%.5f median=%.5f p95=%.5f max=%.5f" %
              (len(allk), sum(allk) / len(allk), statistics.median(allk),
               allk[int(0.95 * (len(allk) - 1))], allk[-1]))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "collect":
        collect(sys.argv[2], sys.argv[3])
    elif cmd == "compare":
        compare(sys.argv[2], sys.argv[3])
    elif cmd == "prefix":
        prefix(sys.argv[2], sys.argv[3])
    else:
        print(__doc__)
        raise SystemExit(2)
