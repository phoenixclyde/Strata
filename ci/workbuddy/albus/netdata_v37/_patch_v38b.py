# -*- coding: utf-8 -*-
"""v38b：JS 跟随 v38 结构重写（总览只留聚合 KPI、主机三栏、存储行改「标题+元信息+读数+状态」）。"""
import io, hashlib

P = r"D:/workbuddy_space/strata_ws/albus/netdata_v37/gpu.html"
s = io.open(P, "rb").read().decode("utf-8")

# ---------------- 1) 工具：KPI 写值 / 成对单位 ----------------
old = '''function rateTxt(kib){'''
new = '''// KPI 值 + 动态单位：失败时整格写 --，不留半截单位
function setKpi(id, n, u){
  var e = $(id); if (!e) return;
  var v = (n === null || n === undefined || n === "" || n === "--") ? "--" : String(n);
  e.innerHTML = v + (u ? "<small>" + u + "</small>" : "");
}
// 成对数量用**同一个单位**（读/写、收/发）：否则一行里 MiB/s 与 KiB/s 并排，读者要自己做除法
function pairUnits(a, b, base, hiU, loU, div){
  if (!hasNum(a) || !hasNum(b)) return null;
  var big = Math.max(a, b) >= base;
  return { a: big ? a / div : a, b: big ? b / div : b, u: big ? hiU : loU };
}
function rateTxt(kib){'''
assert s.count(old) == 1
s = s.replace(old, new)

# ---------------- 2) renderOverview ----------------
i = s.find('function renderOverview(){')
j = s.find('// --- 单卡静态指标', i)
assert i > 0 and j > i
newOV = '''function renderOverview(){
  var L = state.live, names = [];
  if (hasNum(L.amdUtil)) names.push("MI50");
  if (hasNum(L.nvdUtil)) names.push("2070");

  // 1) 整机功耗 = CPU 封装 + 内存域 + 双卡（严格全有；缺一路就 --，不做部分和）
  var pwN = [], pwMiss = [];
  function pwTake(v, name){
    if (hasNum(v)){ pwN.push(name + " " + fmt(v, 0)); return v; }
    pwMiss.push(name); return null;
  }
  var pCpu = pwTake(L.cpuPower, "CPU");
  var pDram = pwTake(L.cpuDram, "内存");
  var pAmd = pwTake(L.amdPower, "MI50");
  var pNvd = pwTake(L.nvdPower, "2070");
  var pwSum = (pCpu !== null && pDram !== null && pAmd !== null && pNvd !== null)
              ? (pCpu + pDram + pAmd + pNvd) : null;
  setKpi("ov-power", pwSum === null ? null : fmt(pwSum, 1), "W");
  setText("ov-power-sub", pwSum === null
    ? ("缺 " + pwMiss.join("/") + "，不做部分和")
    : ("CPU " + fmt(pCpu, 0) + " · 内存 " + fmt(pDram, 0) + " · 双卡 " + fmt(pAmd + pNvd, 0)));
  var pvK = $("ov-k-power");
  if (pvK) pvK.title = "实测四项合计 = CPU 封装（RAPL package-0）+ 内存域（RAPL dram）+ MI50 PPT + RTX 2070。"
    + "本机无 IPMI/BMC（X99-CH8，无 /dev/ipmi*）、也无功率计 => **墙插功耗软件不可测**；"
    + "本值不含主板/PCH、两块 SSD、风扇、网卡与电源转换损耗，因此是下界。";

  // 2) GPU 利用率（两卡平均；单卡明细进副标题，不再单列三行）
  var us = [];
  if (hasNum(L.amdUtil)) us.push(L.amdUtil);
  if (hasNum(L.nvdUtil)) us.push(L.nvdUtil);
  setKpi("ov-util", us.length ? fmt(avgOf(us), 1) : null, "%");
  setText("ov-util-sub", us.length
    ? ("MI50 " + fmt(L.amdUtil, 0) + " · 2070 " + fmt(L.nvdUtil, 0))
    : "无数据");

  // 3) 显存合计
  var vUsed = 0, vTot = 0;
  if (hasNum(L.amdVramPct) && state.amdVramTotal){ vUsed += L.amdVramPct / 100 * state.amdVramTotal; vTot += state.amdVramTotal; }
  if (hasNum(L.nvdUsedB)){ vUsed += L.nvdUsedB; vTot += (L.nvdTotalB || 0); }
  var vPct = vTot ? vUsed / vTot * 100 : null;
  setKpi("ov-vram", fmt(vPct, 1), "%");
  setText("ov-vram-sub", vTot ? (bytes(vUsed) + " / " + bytes(vTot)) : "无数据");
  kpiClass("ov-k-vram", lvlOf(vPct, TH.vram));

  // 4) CPU
  setKpi("ov-cpu", fmt(L.cpuPct, 1), "%");
  setText("ov-cpu-sub", (state.cores ? state.cores + " 线程" : "")
    + (hasNum(L.cpuFreq) ? (state.cores ? " · " : "") + fmt(L.cpuFreq, 0) + " MHz" : ""));
  kpiClass("ov-k-cpu", lvlOf(L.cpuPct, TH.cpu));

  // 5) 主机内存
  setKpi("ov-ram", fmt(L.ramPct, 1), "%");
  setText("ov-ram-sub", (hasNum(L.ramTotalB) && L.ramTotalB > 0)
    ? (bytes(L.ramUsedB) + " / " + bytes(L.ramTotalB)) : "");
  kpiClass("ov-k-ram", lvlOf(L.ramPct, TH.ram));

  // 6) 负载
  setText("ov-load", fmt(L.load1, 2));
  setText("ov-load-sub", (hasNum(L.load1) && state.cores) ? ("每核 " + fmt(L.load1 / state.cores, 2)) : "");

  // 7) 磁盘吞吐 = 两块物理盘 读+写（renderSSD 每轮投递）
  var dR = hasNum(L.diskRd) ? L.diskRd : null;
  var dW = hasNum(L.diskWr) ? L.diskWr : null;
  var dp = (dR !== null && dW !== null) ? pairUnits(dR, dW, 1024, "MiB/s", "KiB/s", 1024) : null;
  if (dp){
    var dsum = pairUnits(dR + dW, dR + dW, 1024, "MiB/s", "KiB/s", 1024);
    setKpi("ov-disk", fmt(dsum.a, dsum.u === "MiB/s" ? 1 : 0), dsum.u);
    setText("ov-disk-sub", "读 " + fmt(dp.a, dp.u === "MiB/s" ? 1 : 0) + " · 写 " + fmt(dp.b, dp.u === "MiB/s" ? 1 : 0) + " " + dp.u);
  } else {
    setKpi("ov-disk", null, "");
    setText("ov-disk-sub", "无数据");
  }

  // 8) 网络吞吐 = 收 + 发
  var nR = hasNum(L.netRx) ? L.netRx : null;
  var nT = hasNum(L.netTx) ? L.netTx : null;
  var np = (nR !== null && nT !== null) ? pairUnits(nR, nT, 1000, "Mbit/s", "kbit/s", 1000) : null;
  if (np){
    var nsum = pairUnits(nR + nT, nR + nT, 1000, "Mbit/s", "kbit/s", 1000);
    setKpi("ov-net", fmt(nsum.a, nsum.u === "Mbit/s" ? 2 : 0), nsum.u);
    setText("ov-net-sub", "↓ " + fmt(np.a, np.u === "Mbit/s" ? 2 : 0) + " · ↑ " + fmt(np.b, np.u === "Mbit/s" ? 2 : 0) + " " + np.u);
  } else {
    setKpi("ov-net", null, "");
    setText("ov-net-sub", "无数据");
  }

  // 卡头：在线卡数（原来是 KPI 里的一格，重复；合并到标题行）
  setText("ov-id", names.length + " 卡在线" + (names.length ? " · " + names.join(" + ") : "") + " · 窗口 " + state.win + " s");
}

'''
s = s[:i] + newOV + s[j:]

# ---------------- 3) renderHost ----------------
i = s.find('function renderHost(ids, win){')
j = s.find('// --- 主机补充项', i)
assert i > 0 and j > i
newHost = '''function renderHost(ids, win){
  return Promise.all([
    series(ids.cpu, win), series(ids.ram, win), series(ids.load, Math.min(win, 120)),
    series(ids.net, win), series(ids.io, win), series(ids.disk, 60), series(ids.memAvail, 60)
  ]).then(function(a){
    var cpu = a[0];
    if (cpu && cpu.rows.length){
      var cols = ["user","system","nice","iowait","irq","softirq","steal","guest","guest_nice"];
      var arr = cpu.rows.map(function(r){
        var s = 0;
        cols.forEach(function(c){ var i = cpu.labels.indexOf(c); if (i > 0 && typeof r[i] === "number") s += r[i]; });
        return s;
      });
      var v = arr[arr.length - 1];
      setText("host-cpu-txt", fmt(v, 1) + " %");
      setWidth("host-cpu-bar", v);
      setText("host-util", fmt(v, 1));
      ring("host-ring", v);
      state.live.cpuPct = v;
      state.series.cpuUtil = arr;
      // 内存「已用 %」序列：mem.available + 精确 MemTotal（见 v37 注释）
      var ramS = a[1], ramArr = [], availS = a[6];
      var ramTotalM = (state.mem && hasNum(state.mem.total) && state.mem.total > 0)
        ? state.mem.total / 1048576 : null;
      if (!ramTotalM && ramS && ramS.rows.length){
        var r0 = ramS.rows[ramS.rows.length - 1];
        var gg = function(nm){ var i = ramS.labels.indexOf(nm); return i > 0 && typeof r0[i] === "number" ? r0[i] : 0; };
        ramTotalM = gg("used") + gg("free") + gg("cached") + gg("buffers");
      }
      if (availS && availS.rows.length && ramTotalM){
        ramArr = availS.rows.map(function(r){
          var i = availS.labels.indexOf("avail");
          var av = (i > 0 && typeof r[i] === "number") ? r[i] : null;
          return av === null ? 0 : Math.max(0, (ramTotalM - av) / ramTotalM * 100);
        });
      } else if (ramS && ramS.rows.length){
        ramArr = ramS.rows.map(function(r){
          var g = function(nm){ var i = ramS.labels.indexOf(nm); return i > 0 && typeof r[i] === "number" ? r[i] : 0; };
          var t = g("used") + g("free") + g("cached") + g("buffers");
          return t > 0 ? g("used") / t * 100 : 0;
        });
      }
      drawChart("host-chart", [
        { values: arr, color: "var(--accent)", fill: true },
        { values: ramArr, color: "var(--accent2)", fill: false }
      ], "host-range");
    }
    // 内存三段自洽：已用(total-available) / 可回收(available-free) / 空闲(free)
    var M = state.mem, ram = a[1];
    if (M && hasNum(M.total) && M.total > 0 && hasNum(M.available)){
      var mUsed = Math.max(0, M.total - M.available);
      var mFree = hasNum(M.free) ? Math.max(0, M.free) : 0;
      var mRecl = Math.max(0, M.available - mFree);
      var upct = mUsed / M.total * 100;
      setText("host-ram-txt", bytes(mUsed) + " / " + bytes(M.total) + "  (" + fmt(upct, 1) + "%)");
      setWidth("host-ram-bar", upct);
      setWidth("host-ram-cache", mRecl / M.total * 100);
      setText("host-ram-dtl", "已用 " + bytes(mUsed) + " · 可回收 " + bytes(mRecl) + " · 空闲 " + bytes(mFree)
        + (hasNum(M.unevict) && M.unevict > 0 ? " · 锁定 " + bytes(M.unevict) : ""));
      state.live.ramUsedB = mUsed;
      state.live.ramTotalB = M.total;
      state.live.ramPct = upct;
      var rEl = $("host-ram-bar");
      if (rEl && rEl.parentNode && rEl.parentNode.parentNode){
        rEl.parentNode.parentNode.title = "三段相加 = 物理内存总量：" +
          "已用 " + bytes(mUsed) + "（total − MemAvailable，不可回收） + 可回收 " + bytes(mRecl) +
          "（MemAvailable − MemFree，页缓存里真能腾出的部分） + 空闲 " + bytes(mFree) + "。" +
          "现代 `free`(3.3.17+) 的 used 就是 total − available，与本行一致。";
      }
    } else if (ram && ram.rows.length){
      var usedM = last(ram, "used"), freeM = last(ram, "free"), cacM = last(ram, "cached"), bufM = last(ram, "buffers");
      var totM = (usedM || 0) + (freeM || 0) + (cacM || 0) + (bufM || 0);
      setText("host-ram-txt", bytes((usedM || 0) * 1048576) + " / " + bytes(totM * 1048576) +
        "  (" + fmt(totM ? (usedM || 0) / totM * 100 : 0, 1) + "%)");
      setWidth("host-ram-bar", totM ? (usedM || 0) / totM * 100 : 0);
      setWidth("host-ram-cache", 0);
      setText("host-ram-dtl", "明细不可用（采集器 mem 段缺失）");
      state.live.ramUsedB = (usedM || 0) * 1048576;
      state.live.ramTotalB = totM * 1048576;
      state.live.ramPct = totM ? (usedM || 0) / totM * 100 : null;
    }
    var ld = a[2];
    state.live.load1 = last(ld, "load1");
    // 网络：netdata 把 sent 存成负值，取绝对值才是发送速率（单位 kilobit/s）
    var net = a[3];
    if (net && net.rows.length){
      var vRx = last(net, "received"), vTx = last(net, "sent");
      var rx = vRx === null ? null : Math.abs(vRx);
      var tx = vTx === null ? null : Math.abs(vTx);
      state.live.netRx = rx;
      state.live.netTx = tx;
      var np = (rx !== null && tx !== null) ? pairUnits(rx, tx, 1000, "Mbit/s", "kbit/s", 1000) : null;
      if (np){
        setValU("host-net-rx", fmt(np.a, np.u === "Mbit/s" ? 2 : 1), np.u);
        setValU("host-net-tx", fmt(np.b, np.u === "Mbit/s" ? 2 : 1), np.u);
      }
    }
    // 磁盘读写在 renderSSD 里按两块物理盘逐盘取数（system.io 会把 LVM 的 IO 重复计一遍）
    state.ioFallback = a[4];
  });
}

'''
s = s[:i] + newHost + s[j:]

# ---------------- 4) renderSSD ----------------
i = s.find('// --- 存储条（v37d，主机卡右栏）')
j = s.find('function tick(){', i)
assert i > 0 and j > i
newSSD = '''// --- 存储条（v38，主机卡第三栏）------------------------------------------
// 每盘一行，四段结构：①盘名 + 元信息 ②读 ③写 ④温度 ⑤寿命 ⑥状态。
// 慢变量（容量 / 已用 / 累计写入 / 通电小时）收进元信息一行，快变量（读写）单独成列 ——
// 这样一行里只有两个数字在跳，其余是"这台盘是什么状态"，不会变成一堵小字墙。
// 数据三路：disk.sda|nvme0n1（读写）、health.json.ssd（SMART）、disk_space.*（文件系统已用）。
function rateTxt(kib){
  if (kib === null || kib === undefined || isNaN(kib)) return "--";
  return kib >= 1024 ? (fmt(kib / 1024, 1) + "<small>MiB/s</small>")
                     : (fmt(kib, 0) + "<small>KiB/s</small>");
}
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
    { key: "nvme0n1", chart: state.ids.diskNvme, space: state.ids.spaceNvme, tag: "NVMe" },
    { key: "sda",     chart: state.ids.diskSda,  space: state.ids.spaceRoot, tag: "SATA" }
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
      var usedPct = fsUsedPct(fs);
      var model = m.model || (x.key + "（SMART 未取到）");
      // 健康 ≠ 寿命：真信号是 Critical Warning / Available Spare 低于该盘阈值 / Media Errors
      var hOk = null;
      if (hasNum(m.ok)){
        var crit = hasNum(m.crit) ? m.crit : 0;
        var spareLow = hasNum(m.spare) && hasNum(m.spare_th) && m.spare < m.spare_th;
        var media = hasNum(m.media_err) ? m.media_err : 0;
        hOk = (m.ok === 1) && crit === 0 && !spareLow && media === 0;
      }
      var hTxt = hOk === null ? "未知" : (hOk ? "正常" : "告警");
      var hCls = hOk === null ? "na" : (hOk ? "ok" : "bad");
      var meta = [x.key, hasNum(m.cap) ? bytes(m.cap) : null, x.tag,
        usedPct === null ? null : ("已用 " + fmt(usedPct, 1) + "%"),
        hasNum(m.written) ? (fmt(m.written / 1e9, 0) + " GB 写入") : null,
        hasNum(m.hours) ? (fmt(m.hours, 0) + " h") : null
      ].filter(function(z){ return z; }).join(" · ");
      var lifeTitle = "寿命剩余：" + (m.kind === "nvme" ? "100 − Percentage Used（厂商估算的已耗耐久度）" : "SMART 231/177 归一化值")
        + "。耐久度不等于健康：100 表示额定写入寿命用完，不代表盘坏。"
        + (m.kind === "nvme"
            ? ("本盘 Percentage Used=" + (hasNum(m.life) ? (100 - m.life) : "?") + "%，Available Spare="
               + (hasNum(m.spare) ? m.spare + "%" : "?") + "（阈值 " + (hasNum(m.spare_th) ? m.spare_th + "%" : "?")
               + "），Critical Warning=" + (hasNum(m.crit) ? "0x0" + m.crit : "?")
               + "，Media Errors=" + (hasNum(m.media_err) ? m.media_err : "?") + "。")
            : "SATA 盘的累计写入不显示：属性 241 的单位随厂商而异（32MiB / LBA / 1GiB），本盘不在 smartctl 库内 => 不猜。");
      html += '<div class="drow">'
        + '<div><div class="dname">' + model + '</div><div class="dmeta">' + meta + '</div></div>'
        + '<div class="dio"><div class="k">读</div><div class="v">' + rateTxt(rd) + '</div></div>'
        + '<div class="dio"><div class="k">写</div><div class="v">' + rateTxt(wr) + '</div></div>'
        + '<div class="dio' + lifeLvl + '" title="' + lifeTitle + '"><div class="k">寿命</div><div class="v">'
        +   (life === null ? "--" : fmt(life, 0)) + '<small>%</small></div></div>'
        + '<div class="dstat ' + hCls + '">' + hTxt + '</div>'
        + '</div>';
    });
    var rows = $("disk-rows");
    if (rows) rows.innerHTML = html;
    state.live.diskRd = nIO > 0 ? rdSum : null;
    state.live.diskWr = nIO > 0 ? wrSum : null;
  });
}

'''
s = s[:i] + newSSD + s[j:]

# ---------------- 5) renderHostExtra：CPU 功耗 / 风扇进瓦片 ----------------
old = '''    state.live.cpuFan = last(a[3], "input");
    setText("uptime", "运行 " + uptimeTxt(up));'''
new = '''    state.live.cpuFan = last(a[3], "input");
    // [v38] 这两项原先只在「总览 CPU 行」里出现；该行已删（与卡片重复）=> 归到主机卡瓦片
    setValU("host-cpw", fmt(state.live.cpuPower, 0), "W");
    setValU("host-fan", fmt(state.live.cpuFan, 0), "rpm");
    setText("uptime", "运行 " + uptimeTxt(up));'''
old = old.replace(chr(10), chr(13) + chr(10))
assert s.count(old) == 1, s.count(old)
s = s.replace(old, new)

io.open(P, "wb").write(s.encode("utf-8"))
print("JS 段完成 bytes=%d md5=%s" % (len(s.encode("utf-8")), hashlib.md5(s.encode("utf-8")).hexdigest()))
