# -*- coding: utf-8 -*-
import io
p = r"D:/workbuddy_space/strata_ws/.workbuddy/memory/MEMORY.md"
s = io.open(p, encoding="utf-8").read()
a = "PLE用direct(`--ple-io ram`-45%)"
b = "PLE用direct(ram-45%)"
print("a count", s.count(a))
if s.count(a) == 1:
    s = s.replace(a, b, 1)
c = "read_ms12.6~252s;"
print("c count", s.count(c))
if s.count(c) == 1:
    s = s.replace(c, "", 1)
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("chars", len(s))
