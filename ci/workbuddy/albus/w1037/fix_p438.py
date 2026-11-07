import io

P = "deploy/PROGRESS.tsv"
s = io.open(P, encoding="utf-8").read()
a = "按机主口径「只要不是负优化就跟」⇒ **保留**，`-001`（`5e63174dbd7cc04e5fa1b5fc455b2a73`）退居回滚件。"
b = a + "本轮累计**重启 4 次**（窗口 3 + 装机 1）、停机 178 s。"
if b in s:
    print("note already fixed")
elif a in s:
    s = s.replace(a, b, 1)
    io.open(P, "w", encoding="utf-8", newline="\n").write(s)
    print("note fixed")
else:
    print("WARN note anchor missing")

s = io.open(P, encoding="utf-8").read()
if "\tKW:装机|k10p" in s:
    s = s.replace("\tKW:装机|k10p", "\tKW:k10p|负优化", 1)
    io.open(P, "w", encoding="utf-8", newline="\n").write(s)
    print("kw fixed")
else:
    print("kw already fixed / not found")
