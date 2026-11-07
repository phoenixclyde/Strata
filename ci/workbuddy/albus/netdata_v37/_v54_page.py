# -*- coding: utf-8 -*-
"""v54-2：页面按盘型渲染 SMART 三格 + 累计写入自适应单位 + 健康判据并入 187"""
import io, hashlib

P = r"D:/workbuddy_space/strata_ws/albus/netdata_v37/gpu.html"
s = io.open(P, "rb").read().decode("utf-8")
crlf = "\r\n" in s
s = s.replace("\r\n", "\n")


def rep(a, b, n=1):
    global s
    assert s.count(a) == n, (s.count(a), a[:70])
    s = s.replace(a, b)


# ---------- 1) volTxt：累计写入量自适应单位 ----------
rep("function renderSSD(){",
    "// 累计写入量：NVMe 走 Data Units Written、SATA 走 Device Statistics 的 Logical Sectors Written，\n"
    "// 都是字节数。值域跨三个数量级（606 GB / 13.8 TB），固定 GB 会变成五位数。\n"
    "function volTxt(b){\n"
    "  if (!hasNum(b)) return \"--\";\n"
    "  if (b >= 1e12) return fmt(b / 1e12, 1) + '<small>TB</small>';\n"
    "  if (b >= 1e9)  return fmt(b / 1e9, 0) + '<small>GB</small>';\n"
    "  return fmt(b / 1e6, 0) + '<small>MB</small>';\n"
    "}\n"
    "function renderSSD(){")

# ---------- 2) 健康判据：SATA 的 187 不可纠正也要算进去 ----------
rep("        var media = hasNum(m.media_err) ? m.media_err : 0;\n"
    "        hOk = (m.ok === 1) && crit === 0 && !spareLow && media === 0;",
    "        var media = hasNum(m.media_err) ? m.media_err : 0;\n"
    "        // SATA 的健康判据不同：187 Reported_Uncorrect > 0 就是真的介质不可纠正错误。\n"
    "        //   199 UDMA_CRC 是链路（线缆/背板）错，不归到\"盘坏\"，只上屏标黄，不进健康判定。\n"
    "        var uncorr = hasNum(m.uncorr) ? m.uncorr : 0;\n"
    "        hOk = (m.ok === 1) && crit === 0 && !spareLow && media === 0 && uncorr === 0;")

# ---------- 3) 已写入：走 volTxt ----------
rep("        +   '<div class=\"dv\"><span>已写入</span><b>' + (hasNum(m.written) ? fmt(m.written / 1e9, 0) + '<small>GB</small>' : \"--\") + '</b></div>'",
    "        +   '<div class=\"dv\"><span>已写入</span><b>' + volTxt(m.written) + '</b></div>'")

# ---------- 4) SMART 三格：按盘型 ----------
OLD_SMART = (
    "        + '<div class=\"dsmart\">'\n"
    "        +   '<div class=\"dt\" title=\"Available Spare：NVMe 预留备用块剩余百分比，低于该盘自报阈值才算告警（阈值 '\n"
    "        +     (hasNum(m.spare_th) ? m.spare_th + \"%\" : \"?\") + '）\"><span>可用备用</span><b>'\n"
    "        +     (hasNum(m.spare) && m.spare <= 100 ? m.spare + '<small>%</small>' : \"--\") + '</b></div>'\n"
    "        +   '<div class=\"dt' + (hasNum(m.media_err) && m.media_err > 0 ? \" bad\" : \"\") + '\" title=\"Media Errors：介质不可恢复错误计数\"><span>介质错误</span><b>'\n"
    "        +     (hasNum(m.media_err) ? m.media_err : \"--\") + '</b></div>'\n"
    "        +   '<div class=\"dt' + (hasNum(m.crit) && m.crit !== 0 ? \" bad\" : \"\") + '\" title=\"Critical Warning：NVMe 关键告警位图，全 0 才正常\"><span>关键告警</span><b>'\n"
    "        +     (hasNum(m.crit) ? (m.crit === 0 ? \"0x00\" : \"0x0\" + m.crit) : \"--\") + '</b></div>'\n"
    "        + '</div>'"
)
NEW_SMART = (
    "        + '<div class=\"dsmart\">' + smartCells + '</div>'"
)
rep(OLD_SMART, NEW_SMART)

# 在 dsmart 之前插入 smartCells 的构造
rep("        + '<div class=\"dsmart\">' + smartCells + '</div>'",
    "        + '<div class=\"dsmart\">' + smartCells + '</div>'")

rep("      var sp = sparkSvg(s, 400, 64, spPrev);",
    "      var sp = sparkSvg(s, 400, 64, spPrev);")  # 占位，确保锚点存在

# 在 html 拼接之前定义 smartCells
rep("      html += '<div class=\"dcard\">'",
    "      // SMART 三格：NVMe 与 SATA 的判据本来就不同，按盘型取各自的等价项，不硬凑同一个词。\n"
    "      //   槽位语义一致：备用（耐久余量）/ 介质错误 / 链路或告警。\n"
    "      var smartCells;\n"
    "      if (m.kind === \"sata\"){\n"
    "        smartCells =\n"
    "            '<div class=\"dt\" title=\"180 Unused_Rsvd_Blk_Cnt_Tot：未使用的备用块个数。NVMe 的 Available Spare 是百分比，'\n"
    "          +   'SATA 的等价物是这个计数；它持续变少说明坏块在消耗备用区。\"><span>备用块</span><b>'\n"
    "          +   (hasNum(m.spare) ? fmt(m.spare, 0) : \"--\") + '</b></div>'\n"
    "          + '<div class=\"dt' + (hasNum(m.uncorr) && m.uncorr > 0 ? \" bad\" : \"\") + '\" title=\"187 Reported_Uncorrect：'\n"
    "          +   '不可纠正错误计数，>0 就是真的介质错误（对应 NVMe 的 Media Errors）。\"><span>不可纠正</span><b>'\n"
    "          +   (hasNum(m.uncorr) ? m.uncorr : \"--\") + '</b></div>'\n"
    "          + '<div class=\"dt' + (hasNum(m.crc) && m.crc > 0 ? \" warn\" : \"\") + '\" title=\"199 UDMA_CRC_Error_Count：'\n"
    "          +   'SATA 链路 CRC 校验错，通常来自线缆/背板/接触，不是盘的介质错误；开始上涨说明链路有问题。\">'\n"
    "          +   '<span>CRC 错误</span><b>' + (hasNum(m.crc) ? m.crc : \"--\") + '</b></div>';\n"
    "      } else {\n"
    "        smartCells =\n"
    "            '<div class=\"dt\" title=\"Available Spare：NVMe 预留备用块剩余百分比，低于该盘自报阈值才算告警（阈值 '\n"
    "          +   (hasNum(m.spare_th) ? m.spare_th + \"%\" : \"?\") + '）\"><span>可用备用</span><b>'\n"
    "          +   (hasNum(m.spare) && m.spare <= 100 ? m.spare + '<small>%</small>' : \"--\") + '</b></div>'\n"
    "          + '<div class=\"dt' + (hasNum(m.media_err) && m.media_err > 0 ? \" bad\" : \"\") + '\" title=\"Media Errors：'\n"
    "          +   '介质不可恢复错误计数\"><span>介质错误</span><b>'\n"
    "          +   (hasNum(m.media_err) ? m.media_err : \"--\") + '</b></div>'\n"
    "          + '<div class=\"dt' + (hasNum(m.crit) && m.crit !== 0 ? \" bad\" : \"\") + '\" title=\"Critical Warning：'\n"
    "          +   'NVMe 关键告警位图，全 0 才正常\"><span>关键告警</span><b>'\n"
    "          +   (hasNum(m.crit) ? (m.crit === 0 ? \"0x00\" : \"0x0\" + m.crit) : \"--\") + '</b></div>';\n"
    "      }\n"
    "      html += '<div class=\"dcard\">'")

# ---------- 5) 寿命提示：SATA 段改成说明来源 + 交叉校验的冲突 ----------
rep('            : "SATA 盘的累计写入不显示：属性 241 的单位随厂商而异（32MiB / LBA / 1GiB），本盘不在 smartctl 库内 => 不猜。");',
    '            : ("SATA：取厂商属性 231/177 的归一化值（本盘不在 smartctl 库内，属性名是 smartctl 猜的）。"\n'
    '               + "⚠ 与标准字段不一致：ATA Device Statistics 的 Percentage Used Endurance Indicator = "\n'
    '               + (hasNum(m.endurance_used) ? m.endurance_used + "%" : "?") + "（本属性反推是 "\n'
    '               + (hasNum(m.life) ? (100 - m.life) + "%" : "?") + "）。按实测写入量 "\n'
    '               + (hasNum(m.written) ? fmt(m.written / 1e12, 2) + " TB" : "?") + " / 1 TB 盘 ≈ "\n'
    '               + (hasNum(m.written) ? fmt(m.written / 1e12, 1) : "?") + " 次全盘擦写，两者都无法证伪；此处保留属性值。");')

# ---------- 6) CSS：warn 档 ----------
rep("  .dt.bad b{color:var(--bad)}",
    "  .dt.bad b{color:var(--bad)}\n  .dt.warn b{color:var(--warn)}")

if crlf:
    s = s.replace("\n", "\r\n")
io.open(P, "wb").write(s.encode("utf-8"))
print("OK", len(s.encode("utf-8")), hashlib.md5(s.encode("utf-8")).hexdigest())
