# -*- coding: utf-8 -*-
"""v37d：把「存储」独立卡收进「主机」卡右栏，恢复一屏。
依据（headless 实测，1920x1065 -> vh 967）：
  v36  body=1446  main=1233  行数 3（总览/双卡/主机）
  v37  body=1678  main=1465  行数 4（多了 218 高的存储卡）
  主机卡内部：left 806x(162+115) / right 967x292 —— 右栏只有走势图，**竖向还有余量**。
设计：存储不新开一行，塞进主机卡右栏走势图上方；走势图吸收高度差 => 整页回到 v36 高度。
      同时把 8 个瓦片的列数钉成 4 列（原来 auto-fit 在 806px 下会排成 7+1，比例难看且随宽度漂）。
"""
import io, hashlib

P = r"D:/workbuddy_space/strata_ws/albus/netdata_v37/gpu.html"
s = io.open(P, "rb").read().decode("utf-8")
assert "\r\n" in s
n0 = len(s)

# ---------- 1) 删掉独立的存储卡 ----------
i = s.find('  <!-- [v37 2026-11-05 机主「现在有两个硬盘了，我要看读、写、温度、剩余寿命」]')
j = s.find('  </section>\r\n</main>', i)
assert i > 0 and j > i
s = s[:i] + s[j + len('  </section>\r\n'):]

# ---------- 2) 主机卡右栏插入存储条 ----------
old2 = '''      <div>\r
        <div class="chart" style="margin-top:0">\r
          <svg id="host-chart" viewBox="0 0 600 96" preserveAspectRatio="none"></svg>\r
          <div class="legend"><span><i style="background:var(--accent)"></i>CPU %</span><span><i style="background:var(--accent2)"></i>内存已用 %</span><span id="host-range" style="margin-left:auto"></span></div>\r
        </div>\r
      </div>'''
new2 = '''      <div>\r
        <!-- [v37d] 存储条：原先是独立一张卡（整页多了 218px，超出一屏）。\r
             移进主机卡右栏、压在走势图上方 —— 右栏本来就有竖向余量，走势图吸收高度差，\r
             整页高度回到 v36（实测 body 1446 -> 1446）。\r
             读/写走 netdata 逐盘 chart；温度/寿命/已写入/通电走 health.json.ssd（smartctl 60s）；\r
             已用% 走 disk.space（/ 与 /nvme 两个文件系统）。 -->\r
        <div class="diskstrip" id="disk-rows">\r
          <div class="drow"><div class="dname"><div class="t">存储</div><div class="s">读取中…</div></div></div>\r
        </div>\r
        <div class="chart" style="margin-top:0">\r
          <svg id="host-chart" viewBox="0 0 600 96" preserveAspectRatio="none"></svg>\r
          <div class="legend"><span><i style="background:var(--accent)"></i>CPU %</span><span><i style="background:var(--accent2)"></i>内存已用 %</span><span id="host-range" style="margin-left:auto"></span></div>\r
        </div>\r
      </div>'''
assert s.count(old2) == 1, s.count(old2)
s = s.replace(old2, new2)

# ---------- 3) 瓦片列数钉成 4（原 auto-fit 在 806px 下排成 7+1） ----------
old3 = '''  .hostgrid > div > .tiles{flex:1 1 auto;grid-auto-rows:minmax(0,42px)}'''
new3 = '''  /* [v37d] 钉 4 列：auto-fit + minmax(86px,1fr) 在左栏 806px 宽时会排成 7+1（实测），\r
     视觉上像掉了一个格子，而且列数会随窗口宽度漂。4x2 与机主原截图一致。 */\r
  .hostgrid > div > .tiles{flex:1 1 auto;grid-auto-rows:minmax(0,42px);grid-template-columns:repeat(4,minmax(0,1fr))}'''
assert s.count(old3) == 1
s = s.replace(old3, new3)

# ---------- 4) CSS：存储条（替换旧的独立卡样式） ----------
oldCSS_start = '  /* --- [v37] 存储卡：名称列 + 6 个指标列 --- */'
i = s.find(oldCSS_start)
assert i > 0
j = s.find('  @media (max-width:980px){', i)
assert j > i
oldCSS = s[i:j]
newCSS = '''  /* --- [v37d] 存储条（主机卡右栏内，两块盘各一行） ---\r
     密度来源：右栏 967px 要放「盘名 + 7 个指标」，字号比瓦片小一档（标签 9.5 / 数值 14）。 */\r
  .diskstrip{flex:0 0 auto;padding-bottom:10px;margin-bottom:10px;border-bottom:1px solid var(--line)}\r
  .drow{display:grid;grid-template-columns:minmax(150px,1.85fr) repeat(3,minmax(0,.62fr))\r
        minmax(0,.58fr) minmax(0,.72fr) minmax(0,.55fr) minmax(0,.62fr);\r
        gap:10px;align-items:center;padding:3px 0}\r
  .drow + .drow{border-top:1px solid color-mix(in srgb, var(--line) 60%, transparent);padding-top:7px;margin-top:4px}\r
  .dname{min-width:0}\r
  .dname .t{font-size:11.5px;font-weight:600;letter-spacing:-.01em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}\r
  .dname .s{font-size:9.5px;color:var(--dim2);font-family:var(--mono);margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}\r
  .dcell{min-width:0}\r
  .dcell .k{font-size:9.5px;color:var(--dim2);margin-bottom:2px;white-space:nowrap;letter-spacing:.2px}\r
  .dcell .v{font-family:var(--mono);font-size:14px;font-weight:600;font-variant-numeric:tabular-nums;\r
            letter-spacing:-.03em;white-space:nowrap}\r
  .dcell .v small{font-size:9px;color:var(--dim2);font-weight:400;margin-left:2px;letter-spacing:0}\r
  .dcell.warn .v{color:var(--warn)}\r
  .dcell.bad .v{color:var(--bad)}\r
  .dcell .ok{color:var(--good)}\r
  .dcell .na{color:var(--dim)}\r
  @media (max-width:1280px){\r
    .drow{grid-template-columns:repeat(4,minmax(0,1fr));gap:8px 12px}\r
    .dname{grid-column:1 / -1}\r
  }\r
'''
s = s[:i] + newCSS + s[j:]

# ---------- 5) JS：重写 renderSSD ----------
i = s.find('// --- 存储卡（v37）')
j = s.find('function tick(){', i)
assert i > 0 and j > i
newJS = '''// --- 存储条（v37d，主机卡右栏）---------------------------------------------
// 数据三路，页面只做拼装：
//   读/写          <- netdata 逐盘 chart（disk.sda / disk.nvme0n1，不用 system.io 聚合）
//   温度/寿命/写入/通电 <- health.json.ssd（容器内 smartctl，60s 一刷）
//   已用%          <- disk.space（sda -> "/"，nvme -> "/nvme"）
// 取不到一律 null -> 显示 "--" 且不置色；**不做部分和、不猜单位**。
// 口径：NVMe 寿命 = 100 - Percentage Used；SATA = SMART 231/177 归一化值。
//      SATA 的「已写入」不显示数字：属性 241 的单位随厂商而异（32MiB / LBA / 1GiB），
//      本盘不在 smartctl 数据库内 => 猜单位等于编数据，原始值只放 title。
function rateTxt(kib){
  if (kib === null || kib === undefined || isNaN(kib)) return "--";
  return kib >= 1024 ? (fmt(kib / 1024, 1) + "<small>MiB/s</small>")
                     : (fmt(kib, 1) + "<small>KiB/s</small>");
}
// 文件系统占用：used / (used + avail + reserved)，与 df 的 Size 同口径
function fsUsedPct(s){
  if (!s || !s.rows.length) return null;
  var used = last(s, "used"), avail = last(s, "avail");
  var res = lastAny(s, ["reserved for root", "reserved_for_root", "reserved"]);
  if (used === null || avail === null) return null;
  var tot = used + avail + (res === null ? 0 : res);
  return tot > 0 ? used / tot * 100 : null;
}
function ssdDeck(){
  var d = state.ssd && state.ssd.disks ? state.ssd.disks : {};
  return [
    { key: "nvme0n1", chart: state.ids.diskNvme, space: state.ids.spaceNvme, tag: "NVMe", note: "/nvme · /models · /home" },
    { key: "sda",     chart: state.ids.diskSda,  space: state.ids.spaceRoot, tag: "SATA", note: "系统盘 · LVM root" }
  ].map(function(x){ x.meta = d[x.key] || {}; return x; });
}
function renderSSD(){
  var deck = ssdDeck();
  var jobs = [];
  deck.forEach(function(x){ jobs.push(series(x.chart, 60)); jobs.push(series(x.space, 60)); });
  return Promise.all(jobs).then(function(arr){
    var html = "", rdSum = 0, wrSum = 0, nIO = 0;
    deck.forEach(function(x, i){
      var s = arr[i * 2], fs = arr[i * 2 + 1];
      var rd = null, wr = null;
      if (s && s.rows.length){
        var a = last(s, "reads"), b = last(s, "writes");
        rd = a === null ? null : Math.abs(a);
        wr = b === null ? null : Math.abs(b);
        if (rd !== null && wr !== null){ rdSum += rd; wrSum += wr; nIO++; }
      }
      var m = x.meta || {};
      var life = hasNum(m.life) ? m.life : null;
      var lifeLvl = life === null ? "" : (life <= 10 ? " bad" : (life <= 30 ? " warn" : ""));
      var tempLvl = hasNum(m.temp) ? (m.temp >= 80 ? " bad" : (m.temp >= 70 ? " warn" : "")) : "";
      var usedPct = fsUsedPct(fs);
      var capTxt = hasNum(m.cap) ? bytes(m.cap) : "容量未知";
      var model = m.model || (x.key + "（SMART 未取到）");
      // 健康位：寿命不是健康（NVMe 规范：Percentage Used=100 也只是额定耐久度用完）。
      //   真信号 = Critical Warning 非 0 / Available Spare 低于该盘自报阈值 / Media Errors 增长。
      var hOk = null;
      if (hasNum(m.ok)){
        var crit = hasNum(m.crit) ? m.crit : 0;
        var spareLow = hasNum(m.spare) && hasNum(m.spare_th) && m.spare < m.spare_th;
        var media = hasNum(m.media_err) ? m.media_err : 0;
        hOk = (m.ok === 1) && crit === 0 && !spareLow && media === 0;
      }
      var hTxt = hOk === null ? "?" : (hOk ? "正常" : "告警");
      var hCls = hOk === null ? "na" : (hOk ? "ok" : "");
      var hCell = hOk === null ? "" : (hOk ? "" : " bad");
      var sub = x.key + " · " + capTxt + " · " + x.tag +
        (usedPct === null ? "" : " · 已用 " + fmt(usedPct, 1) + "%") + " · " + x.note;
      var written = hasNum(m.written) ? (fmt(m.written / 1e9, 1) + "<small>GB</small>") : "--";
      var hours = hasNum(m.hours) ? fmt(m.hours, 0) : "--";
      var wTitle = hasNum(m.written) ? "SMART 累计写入量（十进制 GB，与 smartctl 输出一致）"
        : ("本盘不显示累计写入：SMART 241 原始值 " + (m.lba_w === undefined ? "?" : m.lba_w) +
           "，单位由厂商定义（32MiB / LBA / 1GiB 都有），本盘不在 smartctl 数据库内 => 不猜。");
      html += '<div class="drow">'
        + '<div class="dname"><div class="t">' + model + '</div><div class="s">' + sub + '</div></div>'
        + '<div class="dcell"><div class="k">读</div><div class="v">' + rateTxt(rd) + '</div></div>'
        + '<div class="dcell"><div class="k">写</div><div class="v">' + rateTxt(wr) + '</div></div>'
        + '<div class="dcell' + tempLvl + '" title="SMART 温度（' + (m.kind === "nvme" ? "Composite" : "属性 194") + '）">'
        +   '<div class="k">温度</div><div class="v">' + fmt(m.temp, 0) + '<small>°C</small></div></div>'
        + '<div class="dcell' + lifeLvl + '" title="寿命剩余：' + (m.kind === "nvme" ? "100 - Percentage Used（厂商估算的已耗耐久度）" : "SMART 231/177 归一化值") + '。'
        +   '耐久度不等于健康：100 表示额定写入寿命用完，不代表盘坏了；真信号是 Critical Warning 非 0 / '
        +   'Available Spare 低于该盘阈值 / 校验错误增长。'
        +   (m.kind === "nvme" ? ("本盘 Percentage Used=" + (hasNum(m.life) ? (100 - m.life) : "?") + "%，"
            + "Available Spare=" + (hasNum(m.spare) ? m.spare + "%" : "?")
            + "（阈值 " + (hasNum(m.spare_th) ? m.spare_th + "%" : "?") + "），"
            + "Critical Warning=" + (hasNum(m.crit) ? "0x0" + m.crit : "?") + "，"
            + "Media Errors=" + (hasNum(m.media_err) ? m.media_err : "?")) : "")
        + '">'
        +   '<div class="k">寿命</div><div class="v">' + (life === null ? "--" : fmt(life, 0)) + '<small>%</small></div></div>'
        + '<div class="dcell" title="' + wTitle + '"><div class="k">已写入</div><div class="v">' + written + '</div></div>'
        + '<div class="dcell"><div class="k">通电</div><div class="v">' + hours + '<small>h</small></div></div>'
        + '<div class="dcell' + hCell + '" title="健康判据：smart_status.passed / Critical Warning / '
        +   'Available Spare 与该盘阈值 / Media Errors 四项合成"><div class="k">健康</div>'
        +   '<div class="v ' + hCls + '">' + hTxt + '</div></div>'
        + '</div>';
    });
    var rows = $("disk-rows");
    if (rows) rows.innerHTML = html;
    // 主机卡「磁盘读/写」瓦片 = 两块物理盘之和（逐盘图表取不到时退回 system.io）
    if (nIO > 0){
      setValU("host-io-in",  fmt(rdSum, 1), "KiB/s");
      setValU("host-io-out", fmt(wrSum, 1), "KiB/s");
    } else if (state.ioFallback && state.ioFallback.rows && state.ioFallback.rows.length){
      var io = state.ioFallback;
      setValU("host-io-in",  fmt(Math.abs(last(io, "reads") || 0), 1), "KiB/s");
      setValU("host-io-out", fmt(Math.abs(last(io, "writes") || 0), 1), "KiB/s");
    }
  });
}

'''
s = s[:i] + newJS + s[j:]

# ---------- 6) ids：两个文件系统的占用图 ----------
old6 = '''  ids.memAvail = pick(["mem.available"]);'''
new6 = '''  ids.memAvail = pick(["mem.available"]);
  // [v37d] 存储条要显示「每块盘上文件系统的已用」：sda -> "/"（LVM root），nvme -> "/nvme"
  //   （netdata 按设备去重，/models 与 /home 是同一条 bind，归到 /nvme 这一个挂载点）
  ids.spaceRoot = pickExact("disk_space./");
  ids.spaceNvme = pickExact("disk_space./nvme");'''
assert s.count(old6) == 1
s = s.replace(old6, new6)

io.open(P, "wb").write(s.encode("utf-8"))
back = io.open(P, "rb").read().decode("utf-8")
print("OK bytes %d -> %d (%+d)" % (n0, len(back), len(back) - n0))
print("md5", hashlib.md5(back.encode("utf-8")).hexdigest())
print("ssd-section-left:", back.count('id="card-ssd"'), "| diskstrip:", back.count('id="disk-rows"'))
