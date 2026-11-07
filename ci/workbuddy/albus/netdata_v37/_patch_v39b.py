# -*- coding: utf-8 -*-
"""v39b：图表去噪 + 主机瓦片补回磁盘读写 + 记分板删掉磁盘/网络两项。"""
import io, hashlib

P = r"D:/workbuddy_space/strata_ws/albus/netdata_v37/gpu.html"
s = io.open(P, "rb").read().decode("utf-8")

def crlf(t):
    return t.replace("\n", "\r\n")

# 1) 网格：5 条虚线 -> 1 条基线 + 1 条顶线（虚线密度是"脏"的主因）
old = '''  // 网格
  for (var g = 0; g <= 4; g++){
    var y = PT + (H - PT - PB) * g / 4;
    parts.push('<line x1="0" y1="' + y.toFixed(1) + '" x2="' + W + '" y2="' + y.toFixed(1) +
               '" stroke="var(--grid)" stroke-width="1" stroke-dasharray="2 5"/>');
  }'''
new = '''  // 网格：只留基线与顶线。原来 5 条 2-5 虚线，在 76px 高的条里等于给图铺了一层点阵，
  // 加上面积渐变会显脏（v39）。数据本身有面积填充，不再需要中间线。
  parts.push('<line x1="0" y1="' + (H - PB).toFixed(1) + '" x2="' + W + '" y2="' + (H - PB).toFixed(1) +
             '" stroke="var(--line)" stroke-width="1"/>');
  parts.push('<line x1="0" y1="' + PT.toFixed(1) + '" x2="' + W + '" y2="' + PT.toFixed(1) +
             '" stroke="var(--line)" stroke-width="1" stroke-dasharray="3 6" opacity=".7"/>');'''
assert s.count(crlf(old)) == 1, s.count(crlf(old))
s = s.replace(crlf(old), crlf(new))

# 2) renderSSD 末尾补：主机瓦片的磁盘读写（v38 重写时丢了这段，瓦片一直是 --）
old2 = '''    state.live.diskRd = nIO > 0 ? rdSum : null;
    state.live.diskWr = nIO > 0 ? wrSum : null;'''
new2 = '''    state.live.diskRd = nIO > 0 ? rdSum : null;
    state.live.diskWr = nIO > 0 ? wrSum : null;
    // [v39] 主机卡瓦片「磁盘读/写」= 两块物理盘之和（逐盘明细在存储表里）
    var eIn = $("host-io-in"), eOut = $("host-io-out");
    if (nIO > 0){
      if (eIn)  eIn.innerHTML  = rateTxt(rdSum);
      if (eOut) eOut.innerHTML = rateTxt(wrSum);
    } else if (state.ioFallback && state.ioFallback.rows && state.ioFallback.rows.length){
      var io = state.ioFallback;
      if (eIn)  eIn.innerHTML  = rateTxt(Math.abs(last(io, "reads") || 0));
      if (eOut) eOut.innerHTML = rateTxt(Math.abs(last(io, "writes") || 0));
    }'''
assert s.count(crlf(old2)) == 1, s.count(crlf(old2))
s = s.replace(crlf(old2), crlf(new2))

# 3) renderOverview：磁盘/网络两块已从记分板移走，删掉对应渲染（元素不存在，调用是空转）
i = s.find('  // 7) 磁盘吞吐 = 两块物理盘 读+写')
j = s.find('  // 卡头：在线卡数', i)
assert i > 0 and j > i
s = s[:i] + ('  // 7/8) 磁盘与网络已移回主机卡瓦片（记分板只放 6 项聚合值）\r\n') + s[j:]

io.open(P, "wb").write(s.encode("utf-8"))
print("OK", len(s.encode("utf-8")), hashlib.md5(s.encode("utf-8")).hexdigest())
