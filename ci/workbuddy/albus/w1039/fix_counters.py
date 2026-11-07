import io

R = "albus/w1039/reply.md"
r = io.open(R, encoding="utf-8").read()

old = "本回合 **重启 0 次 / 停机 0 分钟 / 装机 0 / 回滚 0**（VMM 探针与生产共用 GPU 约 1 秒、不启引擎）；**重启 15 次、停机 3993 s、回滚 0 次、装机 0 次**"
new = "本回合 **重启 2 次 / 停机 78 s / 装机 0 / 回滚 0**（`kvg` 窗口 13:42–13:53，两次重启各 39 s，config 已逐字节还原）；本轮累计 **重启 17 次、停机 4071 s、回滚 0 次、装机 0 次**"
if old not in r:
    # the earlier turns may have rewritten that clause; fall back to the bare counters
    old2 = "**重启 15 次、停机 3993 s、回滚 0 次、装机 0 次**"
    assert old2 in r, "neither anchor found"
    r = r.replace(old2, "**重启 17 次、停机 4071 s、回滚 0 次、装机 0 次**（本次窗口 +2 次 / +78 s）", 1)
    print("patched the bare counters")
else:
    r = r.replace(old, new, 1)
    print("patched the full clause")
io.open(R, "w", encoding="utf-8", newline="\n").write(r)

P = "deploy/PROGRESS.tsv"
s = io.open(P, encoding="utf-8").read()
a = "**⇒ 判决：装机**（不是负优化 + 槽 +11.2% + 增长路径已验证），装后再用同一套协议做一次「在产 vs 回滚件」复测。"
b = a + "本轮累计 **重启 17 次 / 停机 4071 s**（前 15/3993 + 本次 2/78）。"
assert a in s
s = s.replace(a, b, 1)
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("P488 note += cumulative counters")
