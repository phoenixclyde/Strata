# -*- coding: utf-8 -*-
"""v38d：补回 setKpi/pairUnits（v38b 把它们连同旧 rateTxt 一起被切片删掉了，
导致 renderOverview / renderHost 抛 ReferenceError —— 总览 8 格全 "--"、网络瓦片全 "--"）。
另：内存行文案缩短（340px 栏宽会折行）；图表加 max-height 免得高屏把扁平曲线拉成一块空地。"""
import io, hashlib

P = r"D:/workbuddy_space/strata_ws/albus/netdata_v37/gpu.html"
s = io.open(P, "rb").read().decode("utf-8")

anchor = '''function rateTxt(kib){
  if (kib === null || kib === undefined || isNaN(kib)) return "--";
  return kib >= 1024 ? (fmt(kib / 1024, 1) + "<small>MiB/s</small>")
                     : (fmt(kib, 0) + "<small>KiB/s</small>");
}'''.replace("\n", "\r\n")
assert s.count(anchor) == 1, s.count(anchor)

helpers = anchor + '''
// [v38d] 这两个原本跟旧 rateTxt 写在一块，v38b 切片重写时被一并删掉 =>
//   renderOverview/renderHost 里每次调用都抛 ReferenceError（总览 8 格全 "--"、网络瓦片全 "--"）。
//   教训：**切片替换前先列出该区间里定义了哪些函数**，别只盯着要改的那一个。
function setKpi(id, n, u){
  var e = $(id); if (!e) return;
  var v = (n === null || n === undefined || n === "" || n === "--") ? "--" : String(n);
  e.innerHTML = v + (u ? "<small>" + u + "</small>" : "");
}
// 成对数量（读/写、收/发）用**同一个单位**：否则一行里 MiB/s 与 KiB/s 并排，读者要做除法
function pairUnits(a, b, base, hiU, loU, div){
  if (!hasNum(a) || !hasNum(b)) return null;
  var big = Math.max(a, b) >= base;
  return { a: big ? a / div : a, b: big ? b / div : b, u: big ? hiU : loU };
}'''.replace("\n", "\r\n")

s = s.replace(anchor, helpers)

# 内存行：340px 栏宽下 "75.9 GiB / 125.7 GiB (60.3%)" 会折行 -> 去掉空格并降精度
old = '''      setText("host-ram-txt", bytes(mUsed) + " / " + bytes(M.total) + "  (" + fmt(upct, 1) + "%)");'''
new = '''      setText("host-ram-txt", bytes(mUsed) + "/" + bytes(M.total) + " · " + fmt(upct, 1) + "%");'''
assert s.count(old) == 1
s = s.replace(old, new)

# 图表高度上限：高屏时别把一条 0% 的平线拉成 200px 的空地
old2 = '  .card .chart svg{flex:1 1 auto;height:72px;min-height:72px;width:100%;display:block}'
new2 = '  .card .chart svg{flex:1 1 auto;height:72px;min-height:72px;max-height:132px;width:100%;display:block}'
assert s.count(old2) == 1
s = s.replace(old2, new2)

io.open(P, "wb").write(s.encode("utf-8"))
print("OK", len(s.encode("utf-8")), hashlib.md5(s.encode("utf-8")).hexdigest())
