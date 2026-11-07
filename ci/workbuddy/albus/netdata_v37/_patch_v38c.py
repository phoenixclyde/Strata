# -*- coding: utf-8 -*-
"""v38c：让版面「矮屏不溢出、高屏不留白」。
原理：卡片行用 minmax(min-content, Nfr) —— 内容装不下时按 min-content 走（不溢出），
      有余量时按比例分配（图表跟着长高，而不是在卡片底部留一片黑）。
      图表 min-height 72px 是底线：低于这个高度趋势线没法看。
实测基准：1920x1898 视口 vh=967 时自然高约 1000；1443 高时自动撑满。
"""
import io, hashlib

P = r"D:/workbuddy_space/strata_ws/albus/netdata_v37/gpu.html"
s = io.open(P, "rb").read().decode("utf-8")

pairs = [
    # 行分配：不再固定 auto，改成「至少 min-content，余量按 1.15 / 0.95 分」
    ('  main{gap:14px;grid-template-rows:auto auto auto;align-content:start}',
     '  main{gap:14px;grid-template-rows:auto minmax(min-content,1.15fr) minmax(min-content,.95fr);align-content:stretch}'),
    # 图表：吸收本卡余量，但留 72px 底线
    ('  .card .chart{margin-top:14px;flex:0 0 auto}\r\n'
     '  .card .chart svg{flex:0 0 auto;height:80px;min-height:0}',
     '  .card .chart{margin-top:12px;flex:1 1 auto;min-height:0;display:flex;flex-direction:column}\r\n'
     '  .card .chart svg{flex:1 1 auto;height:auto;min-height:72px}'),
    # 主机第三栏：存储条固定，图表吃掉余量
    ('  .hostgrid{grid-template-columns:340px minmax(0,1fr) minmax(0,1.32fr);gap:28px}',
     '  .hostgrid{grid-template-columns:340px minmax(0,1fr) minmax(0,1.32fr);gap:28px;height:100%}\r\n'
     '  .hcol{min-width:0;display:flex;flex-direction:column}\r\n'
     '  .hcol-c .chart{flex:1 1 auto;min-height:0}'),
]

for old, new in pairs:
    old = old.replace("\n", "\r\n") if "\n" in old and "\r\n" not in old else old
    n = s.count(old)
    assert n == 1, (n, old[:60])
    s = s.replace(old, new)

io.open(P, "wb").write(s.encode("utf-8"))
print("OK", len(s.encode("utf-8")), hashlib.md5(s.encode("utf-8")).hexdigest())
