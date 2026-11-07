"""进度计数：读 deploy/PROGRESS.tsv，输出「共几块几条 / 已结多少」。
用法： python tools/progress.py [--md]
"""
import io
import sys

P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
COLS = ["block", "id", "item", "source", "kind", "count", "done", "status", "note", "ref", "kw"]  # W1035: kw = KW:词1|词2（检索键）


def load():
    rows, bad = [], []
    for i, ln in enumerate(io.open(P, encoding="utf-8").read().splitlines(), 1):
        if not ln.strip() or ln.lstrip().startswith("#"):
            continue
        f = ln.split("\t")
        if f[0] == "block":          # 表头
            continue
        if len(f) == 9:                      # 老行没有 ref
            f.append("")
        if len(f) == 10:                     # W1035: 老行没有第 11 列 KW:
            f.append("")
        if len(f) != len(COLS):
            bad.append((i, len(f), ln[:60]))
            continue
        rows.append(dict(zip(COLS, f)))
    return rows, bad


def main():
    rows, bad = load()
    if bad:
        print("!! 列数不对（应为 %d 列）:" % len(COLS))
        for i, n, s in bad:
            print("   line %d: %d 列  %s" % (i, n, s))
    blocks = {}
    for r in rows:
        b = r["block"]
        d = blocks.setdefault(b, {"n": 0, "done": 0, "open": 0, "neg": 0})
        c, k = int(r["count"]), int(r["done"])
        d["n"] += c
        d["done"] += k
        if r["status"] in ("DONE", "DONE_NEG", "NA"):
            d["done"] += 0
        if r["status"] == "OPEN":
            d["open"] += c - k
        if r["status"] in ("DONE_NEG", "NA"):
            d["neg"] += c
    tot = sum(v["n"] for v in blocks.values())
    done = sum(v["done"] for v in blocks.values())
    # 死块池单列
    dead = sum(int(r["count"]) - int(r["done"]) for r in rows if r["id"] == "D28")
    dead_n = sum(int(r["count"]) for r in rows if r["id"] == "D28")
    print("块 %d ／ 条 %d ／ 已结 %d（%.1f%%）" % (len(blocks), tot, done, 100.0 * done / tot))
    print("  主线（不含 %d 个死块）= %d 条：已结 %d（%.1f%%）" %
          (dead_n, tot - dead_n, done, 100.0 * done / max(1, tot - dead_n)))
    print("  死块池：%d/%d" % (dead_n - dead, dead_n))
    print()
    if "--md" in sys.argv:
        print("| 块 | 条 | 已结 | 进度 |")
        print("|---|---:|---:|---:|")
        for b, v in blocks.items():
            print("| %s | %d | %d | %.0f%% |" % (b, v["n"], v["done"], 100.0 * v["done"] / v["n"]))
    else:
        for b, v in blocks.items():
            print("  %-12s %3d 条  已结 %3d  %5.1f%%" % (b, v["n"], v["done"], 100.0 * v["done"] / v["n"]))
    left = [r for r in rows if r["status"] == "OPEN"]
    if "--open" not in sys.argv:
        return
    print("\n未动 %d 组：" % len(left))
    for r in left:
        print("  - %s %s（%s）" % (r["block"], r["id"], r["item"]))


if __name__ == "__main__":
    main()
