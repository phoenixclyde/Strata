import io

P = "deploy/PROGRESS.tsv"
s = io.open(P, encoding="utf-8").read()
fix = [
    ("\tKW:decode 分解|CPU 专家|双峰\n", "\tKW:400 个窗口|CPU 专家|占全窗\n"),
    ("\tKW:天花板|首请求|搭车\n", "\tKW:天花板|可重复|保留\n"),
]
for a, b in fix:
    assert a in s, a
    s = s.replace(a, b, 1)
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("kw fixed")
