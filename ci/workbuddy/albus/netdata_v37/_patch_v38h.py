# -*- coding: utf-8 -*-
import io, hashlib
P = r"D:/workbuddy_space/strata_ws/albus/netdata_v37/gpu.html"
s = io.open(P, "rb").read().decode("utf-8")
old = '      setText("host-ram-dtl", "可回收 " + bytes(mRecl) + " · 空闲 " + bytes(mFree));'
new = ('      // 只写一次单位：\'可回收 43.9 · 空闲 88.4 GiB\'（原写法两段各带一次 GiB，316px 栏宽会截断）\r\n'
       '      setText("host-ram-dtl", "可回收 " + fmt(mRecl / 1073741824, 1)\r\n'
       '        + " · 空闲 " + fmt(mFree / 1073741824, 1) + " GiB");')
assert s.count(old) == 1, s.count(old)
s = s.replace(old, new)
io.open(P, "wb").write(s.encode("utf-8"))
print("OK", hashlib.md5(s.encode("utf-8")).hexdigest())
