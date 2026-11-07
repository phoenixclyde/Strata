# -*- coding: utf-8 -*-
"""v37d-3：存储条字号微调（标签 9.5 -> 10px，副标题 9.5 -> 10px）。
理由：这一条的标签比瓦片标签（11px）小一档是刻意的（密度更高），但 9.5 在 1080p 下偏小；
      实测条高 94px，两行各 34px，还有余量容纳 +0.5px。
"""
import io, hashlib

P = r"D:/workbuddy_space/strata_ws/albus/netdata_v37/gpu.html"
s = io.open(P, "rb").read().decode("utf-8")

pairs = [
    ('  .dname .s{font-size:9.5px;', '  .dname .s{font-size:10px;'),
    ('  .dcell .k{font-size:9.5px;', '  .dcell .k{font-size:10px;'),
]
for old, new in pairs:
    assert s.count(old) == 1, (old, s.count(old))
    s = s.replace(old, new)

io.open(P, "wb").write(s.encode("utf-8"))
print("OK", len(s.encode("utf-8")), hashlib.md5(s.encode("utf-8")).hexdigest())
