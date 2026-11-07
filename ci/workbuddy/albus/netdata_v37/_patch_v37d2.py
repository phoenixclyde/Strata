# -*- coding: utf-8 -*-
"""v37d-2 + 行尾归一：先全文件 CRLF 归一（v37d 插入的 JS 段是 LF，混行尾），再改瓦片单位。"""
import io, hashlib

P = r"D:/workbuddy_space/strata_ws/albus/netdata_v37/gpu.html"
raw = io.open(P, "rb").read().decode("utf-8")
before_crlf = raw.count("\r\n")
only_lf = raw.count("\n") - before_crlf
print("归一前: CRLF=%d 纯LF=%d" % (before_crlf, only_lf))

s = raw.replace("\r\n", "\n").replace("\n", "\r\n")

old = '''    if (nIO > 0){\r
      setValU("host-io-in",  fmt(rdSum, 1), "KiB/s");\r
      setValU("host-io-out", fmt(wrSum, 1), "KiB/s");\r
    } else if (state.ioFallback && state.ioFallback.rows && state.ioFallback.rows.length){\r
      var io = state.ioFallback;\r
      setValU("host-io-in",  fmt(Math.abs(last(io, "reads") || 0), 1), "KiB/s");\r
      setValU("host-io-out", fmt(Math.abs(last(io, "writes") || 0), 1), "KiB/s");\r
    }'''
new = '''    // [v37d] 瓦片也走 rateTxt：两块盘合计在模型加载瞬间是 1.7 GiB/s，\r
    //   原样写 KiB/s 会变成 1750896.0 这种七位数，和存储条里的 1707.6 MiB/s 对不上。\r
    var eIn = $("host-io-in"), eOut = $("host-io-out");\r
    if (nIO > 0){\r
      if (eIn)  eIn.innerHTML  = rateTxt(rdSum);\r
      if (eOut) eOut.innerHTML = rateTxt(wrSum);\r
    } else if (state.ioFallback && state.ioFallback.rows && state.ioFallback.rows.length){\r
      var io = state.ioFallback;\r
      if (eIn)  eIn.innerHTML  = rateTxt(Math.abs(last(io, "reads") || 0));\r
      if (eOut) eOut.innerHTML = rateTxt(Math.abs(last(io, "writes") || 0));\r
    }'''
n = s.count(old)
assert n == 1, n
s = s.replace(old, new)

io.open(P, "wb").write(s.encode("utf-8"))
back = io.open(P, "rb").read().decode("utf-8")
print("归一后: CRLF=%d 纯LF=%d" % (back.count("\r\n"), back.count("\n") - back.count("\r\n")))
print("OK", len(back.encode("utf-8")), hashlib.md5(back.encode("utf-8")).hexdigest())
