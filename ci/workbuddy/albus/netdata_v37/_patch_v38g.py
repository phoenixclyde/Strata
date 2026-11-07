# -*- coding: utf-8 -*-
import io, hashlib
P = r"D:/workbuddy_space/strata_ws/albus/netdata_v37/gpu.html"
s = io.open(P, "rb").read().decode("utf-8")
old = '''      setText("host-ram-dtl", "可回收 " + bytes(mRecl) + " · 空闲 " + bytes(mFree)
        + (hasNum(M.unevict) && M.unevict > 0 ? " · 锁定 " + bytes(M.unevict) : ""));'''.replace("\n", "\r\n")
new = '''      // 316px 栏宽只放得下两段；锁定(mlocked)是解释性信息，挪进 title
      setText("host-ram-dtl", "可回收 " + bytes(mRecl) + " · 空闲 " + bytes(mFree));'''.replace("\n", "\r\n")
assert s.count(old) == 1, s.count(old)
s = s.replace(old, new)
io.open(P, "wb").write(s.encode("utf-8"))
print("OK", hashlib.md5(s.encode("utf-8")).hexdigest())
