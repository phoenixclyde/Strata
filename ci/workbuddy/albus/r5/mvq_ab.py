#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W806b 分析器：从驱动器输出 + 客户端 JSON 里取每臂的 TTFT / decode / 单发 read 时间。
   口径（沿用 W801/W803）：
     - TTFT = mt_chat 的 prompt_ms（每轮），decode = decode_ms（每轮生成 64 token）
     - 单发 = mt_read 的 prompt_ms（fresh prompt，无复用）
   一切只做"同臂内中位 + 臂间差"，不合并 wall（decode 会盖住 TTFT）。
"""
import json, os, re, statistics as st, sys

DRV = sys.argv[1] if len(sys.argv) > 1 else None
JSONDIR = os.path.dirname(DRV) if DRV else "."

def parse_driver(path):
    """返回 {arm: {"chat": [(turn, read, prompt_ms, decode_ms)], "chunks": [...], "meta": {}}}"""
    arms, cur = {}, None
    for ln in open(path, encoding="utf-8", errors="replace"):
        m = re.match(r"=== ARM (\w) bin=(\w+) mmvq=(\d) maxt=(\S+) ready=(\d+)s", ln)
        if m:
            cur = m.group(1)
            arms[cur] = {"bin": m.group(2), "mmvq": m.group(3), "maxt": m.group(4),
                         "chat": [], "meta": {}, "read": {}}
            continue
        if cur is None:
            continue
        m = re.search(r"BINCHECK arm=\w+ want=(\w+)", ln)
        if m:
            arms[cur]["bincheck"] = "OK" if ln.rstrip().endswith("OK") else "MISMATCH"
            continue
        m = re.search(r"ENVCHECK want=(\d+) got=(\d+) img_extra=(\d+) (\w+)", ln)
        if m:
            arms[cur]["envcheck"] = "%s/%s %s" % (m.group(1), m.group(2), m.group(4))
            continue
        # mt_chat 的轮次行
        m = re.search(r"^T(\d+)\s+ask=\s*(\d+)\s+read=\s*(\d+)\s+reused=\s*\d+\s+prompt_ms=\s*([0-9.]+)\s+decode_ms=\s*([0-9.]+)", ln)
        if m:
            arms[cur]["chat"].append((int(m.group(1)), int(m.group(3)), float(m.group(4)), float(m.group(5))))
            # 注意：驱动器每臂跑两次 mt_chat。第二次的 T2/T3 会被会话缓存整段命中（read=5），与第一次不可比
            # => 只保留前 4 行（第一次，read 101/316/125/340）。见 W806 §4.3。
            continue
        m = re.search(r"read_results=(\d+)", ln)
        if m:
            arms[cur]["meta"]["read_results"] = int(m.group(1))
        m = re.search(r"prompt (\d+) tokens = (\d+) reused \+ (\d+) read in ([0-9]+) ms", ln)
        if m:
            arms[cur]["meta"].setdefault("chunk", []).append((int(m.group(1)), int(m.group(3)), int(m.group(4))))
    # 单发结果
    for a in arms:
        f = os.path.join(JSONDIR, "w806b_read_%s.json" % a)
        if os.path.exists(f):
            try:
                d = json.load(open(f, encoding="utf-8"))["results"]
                # mt_read.py 的字段：target / prompt_tokens / wall_s（没有 prompt_ms）
                for r in d:
                    if r.get("ok"):
                        arms[a]["read"].setdefault(r["target"], []).append(r["wall_s"] * 1000.0)
                arms[a]["read"] = {k: med([x for x in v if x is not None]) for k, v in arms[a]["read"].items()}
            except Exception as e:
                arms[a]["meta"]["read_err"] = str(e)
    return arms

def med(xs):
    return st.median(xs) if xs else None

def main():
    arms = parse_driver(DRV)
    order = [a for a in "ABCDE" if a in arms]
    print("== 臂一览 ==")
    print("%-4s %-4s %-6s %-7s %-9s %-12s %s" % ("arm", "bin", "mmvq", "maxT", "bincheck", "envcheck", "read_n"))
    for a in order:
        v = arms[a]
        print("%-4s %-4s %-6s %-7s %-9s %-12s %s" % (a, v["bin"], v["mmvq"], v["maxt"],
                                                     v.get("bincheck", "?"), v.get("envcheck", "?"),
                                                     v["meta"].get("read_results", "-")))

    # 每臂把两次 mt_chat 按轮次聚合（同轮两次取中位）
    print("\n== 多轮 chat（每轮两次同配置，取中位；read 为实测）==")
    for a in order:
        arms[a]["chat"] = arms[a]["chat"][:4]      # 只取第一次（第二次 read=5 不可比）
    hdr = "%-4s" % "arm"
    turns = sorted({t for a in order for (t, _, _, _) in arms[a]["chat"]})
    reads = {}
    for t in turns:
        hdr += "  T%-2d read  TTFT      dec" % t
    print(hdr)
    for a in order:
        line = "%-4s" % a
        for t in turns:
            rows = [(r, p, d) for (tt, r, p, d) in arms[a]["chat"] if tt == t]
            if not rows:
                line += "  %-8s" % "-"
                continue
            reads[t] = int(med([r for (r, _, _) in rows]))
            line += "  %-6s %6.0f  %5.0f" % (med([r for (r, _, _) in rows]), med([p for (_, p, _) in rows]),
                                             med([d for (_, _, d) in rows]))
        print(line)

    # 单发 read
    print("\n== 单发 fresh prompt（mt_read，每档 2 次，取中位）==")
    sizes = sorted({s for a in order for s in arms[a]["read"]})
    if sizes:
        print("%-4s %s" % ("arm", "".join("  tgt=%-4d" % s for s in sizes)))
        for a in order:
            print("%-4s %s" % (a, "".join("  %11s" % (("%.0f" % arms[a]["read"][s]) if s in arms[a]["read"] else "-")
                                          for s in sizes)))

    # 差（对 A）
    if "A" in arms:
        print("\n== 相对 A 的差（负=更快）==")
        for a in order:
            if a == "A":
                continue
            cells = []
            for t in turns:
                ra = [(r, p) for (tt, r, p, _) in arms["A"]["chat"] if tt == t]
                rb = [(r, p) for (tt, r, p, _) in arms[a]["chat"] if tt == t]
                if ra and rb:
                    ma, mb = med([p for (_, p) in ra]), med([p for (_, p) in rb])
                    cells.append("T%d TTFT %+.1f%%" % (t, 100 * (mb - ma) / ma))
            da = [d for (_, _, _, d) in arms["A"]["chat"]]
            db = [d for (_, _, _, d) in arms[a]["chat"]]
            if da and db:
                cells.append("decode 合计 %+.1f%%" % (100 * (sum(db) - sum(da)) / sum(da)))
            for s in sizes:
                if s in arms["A"]["read"] and s in arms[a]["read"]:
                    va, vb = arms["A"]["read"][s], arms[a]["read"][s]
                    cells.append("read%d %+.1f%%" % (s, 100 * (vb - va) / va))
            print("%-4s %s" % (a, " | ".join(cells)))

if __name__ == "__main__":
    main()
