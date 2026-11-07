# -*- coding: utf-8 -*-
"""断言式补丁：gpu.html v36 -> v37（2026-11-05）
改动摘要（每条都是「判据/口径」级，不只是加格子）：
  P1  总览 KPI1：GPU 合计功耗 -> 整机功耗（实测四项合计，严格全有）
  P2  主机内存：改用 /proc/meminfo 全量（已用=total-available，缓存单列，堆叠条）
  P3  主机磁盘读写：不再用 system.io 聚合（LVM 会重复计数），改两物理盘相加
  P4  新增「存储」卡：两块盘 读/写/温度/寿命/已写入/通电
  P5  顶栏：常驻服务归因（strata* --serve + 生产包装进程），判决文案改写，
      状态格标 +服务，SWAP 判据改相对阈值
规则：每条 old 必须命中恰 1 次；写盘后逐条读回断言；CRLF 原样保留。
"""
import io, hashlib, shutil

SRC = r"D:/workbuddy/netdata-dashboard/gpu.html"
DST = r"D:/workbuddy_space/strata_ws/albus/netdata_v37/gpu.html"

raw = io.open(SRC, "rb").read()
s = raw.decode("utf-8").replace("\r\n", "\n")
assert "\r\n" in raw.decode("utf-8"), "源文件不是 CRLF，停止（行尾约定变了需重新确认）"
shutil.copyfile(SRC, DST + ".v36.bak")

P = []
def add(tag, kind, old, new):
    P.append((tag, kind, old, new))

# ---------------- P1 总览 KPI1 ----------------
add("P1a", "modify", '''      <div class="kpi" id="ov-k-power">
        <div class="k">GPU 合计功耗</div>''', '''      <div class="kpi" id="ov-k-power">
        <div class="k">整机功耗（实测）</div>''')

add("P1b", "modify", '''  // 1) GPU 合计功耗
  var pw = [], pwN = [];
  if (hasNum(L.amdPower)){ pw.push(L.amdPower); pwN.push("MI50 " + fmt(L.amdPower, 0)); }
  if (hasNum(L.nvdPower)){ pw.push(L.nvdPower); pwN.push("2070 " + fmt(L.nvdPower, 0)); }
  var pwSum = pw.length ? pw.reduce(function(a, b){ return a + b; }, 0) : null;
  setText("ov-power", fmt(pwSum, 1));
  setText("ov-power-sub", pwN.length ? pwN.join(" + ") : "无数据");''',
'''  // 1) 整机功耗（实测四项合计：CPU 封装 + 内存域 + 双卡）
  //    [v37 2026-11-05 机主要「整机」而不是两张卡相加]
  //    本机没有 IPMI/BMC（HUANANZHI X99-CH8，实测无 /dev/ipmi*、ipmitool 未装），
  //    也没有墙插功率计 => **整机墙插功耗在软件层不可测**。能实测的只有四个电表：
  //      cpu.powercap_intel_rapl_zone/package-0   CPU 封装（Socket(s)=1，单路，覆盖全部 22 核）
  //      cpu.powercap_intel_rapl_subzones/dram    内存域
  //      sensors.power_amdgpu-pci-0500/PPT        MI50 板级
  //      nvidia_smi/gpu_power_draw                RTX 2070 板级
  //    未计入：主板/PCH、两块 SSD、风扇、网卡、电源转换损耗 => 本值是**下界**。
  //    这一条必须写在 title 里，不许把「四项合计」冒充成「墙插读数」。
  var pwN = [], pwMiss = [];
  function pwTake(v, name){
    if (hasNum(v)){ pwN.push(name + " " + fmt(v, 0)); return v; }
    pwMiss.push(name); return null;
  }
  var pCpu = pwTake(L.cpuPower, "CPU");
  var pDram = pwTake(L.cpuDram, "内存");
  var pAmd = pwTake(L.amdPower, "MI50");
  var pNvd = pwTake(L.nvdPower, "2070");
  // 严格全有：缺任何一路就 --（部分和会把整机功耗报小，比报不出更糟）
  var pwSum = (pCpu !== null && pDram !== null && pAmd !== null && pNvd !== null)
              ? (pCpu + pDram + pAmd + pNvd) : null;
  setText("ov-power", fmt(pwSum, 1));
  setText("ov-power-sub", pwSum !== null
            ? (pwN.join(" + ") + " · 不含主板/盘/电源损耗")
            : ("缺 " + pwMiss.join("/") + " · 不做部分和"));
  var pvK = $("ov-k-power");
  if (pvK) pvK.title = "实测四项合计 = CPU 封装（RAPL package-0）+ 内存域（RAPL dram）"
    + " + MI50 PPT + RTX 2070 板级。本机无 IPMI/BMC（X99-CH8，无 /dev/ipmi*）、"
    + "也无功率计 => **墙插功耗软件不可测**；本值不含主板/PCH、两块 SSD、风扇、"
    + "网卡与电源转换损耗，因此是下界。要真值：带计量的墙插/插排，或换带 BMC 的板子。";''')

# ---------------- P2 主机内存 ----------------
add("P2a", "modify", '''      // 内存占用 % 序列：used / (used+free+cached+buffers)，与 CPU 同为百分比可共轴
      var ramS = a[1], ramArr = [];
      if (ramS && ramS.rows.length){
        ramArr = ramS.rows.map(function(r){
          var g = function(nm){ var i = ramS.labels.indexOf(nm); return i > 0 && typeof r[i] === "number" ? r[i] : 0; };
          var t = g("used") + g("free") + g("cached") + g("buffers");
          return t > 0 ? g("used") / t * 100 : 0;
        });
      }''',
'''      // 内存「已用 %」序列 —— [v37] 改用 mem.available（netdata 的 MemAvailable），
      //   已用 = total - available，与 `free` 的 used 同义；旧式 used/(used+free+cached+buffers)
      //   分子不含缓存、分母漏 SReclaimable => 与 free 对不上（盘上缓存几十 GB 时差得更多）。
      //   total 取采集器给的精确 MemTotal（不随窗口变），缺失时退回四维之和。
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
      }''')

add("P2b", "modify", '''    var ram = a[1];
    if (ram && ram.rows.length){
      var usedM = last(ram, "used"), freeM = last(ram, "free"), cacM = last(ram, "cached"), bufM = last(ram, "buffers");
      var totM = (usedM || 0) + (freeM || 0) + (cacM || 0) + (bufM || 0);
      setText("host-ram-txt", bytes((usedM || 0) * 1048576) + " / " + bytes(totM * 1048576) +
        "  (" + fmt(totM ? (usedM || 0) / totM * 100 : 0, 1) + "%)");
      setWidth("host-ram-bar", totM ? (usedM || 0) / totM * 100 : 0);
      state.live.ramUsedB = (usedM || 0) * 1048576;
      state.live.ramTotalB = totM * 1048576;
      state.live.ramPct = totM ? (usedM || 0) / totM * 100 : null;
    }''',
'''    // [v37 2026-11-05 机主「内存那个条子有问题，不是系统所有内存占用情况」]
    //   改口径：**全量三段**，不再只报「netdata 的 used」。
    //     已用 = total - available        （不可回收部分，= `free` 的 used）
    //     缓存 = cached + buffers + SReclaimable（可回收，但确实占着物理内存）
    //     可用 = MemAvailable             （含可回收缓存，系统真正能立刻给的量）
    //   旧实现分母是 system.ram 的四维和（漏 SReclaimable），分子是 used（不含缓存），
    //   于是「缓存吃掉几十 GB」这件事在条上完全看不见 —— 那正是他说的「不是全部」。
    var M = state.mem;
    var ram = a[1];
    if (M && hasNum(M.total) && M.total > 0 && hasNum(M.available)){
      var mUsed = Math.max(0, M.total - M.available);
      var mCache = Math.max(0, (M.cached || 0) + (M.buffers || 0) + (M.sreclaim || 0));
      var upct = mUsed / M.total * 100;
      setText("host-ram-txt", bytes(mUsed) + " / " + bytes(M.total) + "  (" + fmt(upct, 1) + "%)");
      setWidth("host-ram-bar", upct);
      setWidth("host-ram-cache", Math.min(100 - upct, mCache / M.total * 100));
      setText("host-ram-dtl", "缓存 " + bytes(mCache) + "（可回收） · 可用 " + bytes(M.available));
      state.live.ramUsedB = mUsed;
      state.live.ramTotalB = M.total;
      state.live.ramPct = upct;
      state.live.ramCacheB = mCache;
    } else if (ram && ram.rows.length){
      // 采集器没给 mem（health.json 未到/解析失败）时退回旧口径，但**照实标注**，
      // 不让「退化路径」看起来和正常一样。
      var usedM = last(ram, "used"), freeM = last(ram, "free"), cacM = last(ram, "cached"), bufM = last(ram, "buffers");
      var totM = (usedM || 0) + (freeM || 0) + (cacM || 0) + (bufM || 0);
      setText("host-ram-txt", bytes((usedM || 0) * 1048576) + " / " + bytes(totM * 1048576) +
        "  (" + fmt(totM ? (usedM || 0) / totM * 100 : 0, 1) + "%)");
      setWidth("host-ram-bar", totM ? (usedM || 0) / totM * 100 : 0);
      setWidth("host-ram-cache", 0);
      setText("host-ram-dtl", "缓存明细不可用（采集器 mem 缺失，口径为 system.ram 四维）");
      state.live.ramUsedB = (usedM || 0) * 1048576;
      state.live.ramTotalB = totM * 1048576;
      state.live.ramPct = totM ? (usedM || 0) / totM * 100 : null;
    }''')

# ---------------- P3 磁盘读写不再用 system.io ----------------
add("P3", "modify", '''    // 磁盘吞吐：system.io 的**数据标签**是 reads / writes（不是 charts 接口里列的 in / out）。
    // 写成 "in"/"out" 会让 colOf 静默退回第 1 列，"磁盘读"和"磁盘写"显示同一个数（2026-09-20 修正）。
    // writes 同样是负值存放，取绝对值。
    var io = a[4];
    if (io && io.rows.length){
      var vRd = last(io, "reads"), vWr = last(io, "writes");
      setValU("host-io-in",  fmt(vRd === null ? null : Math.abs(vRd), 1), "KiB/s");
      setValU("host-io-out", fmt(vWr === null ? null : Math.abs(vWr), 1), "KiB/s");
    }''',
'''    // 磁盘吞吐 —— [v37] 改由 renderSSD 按**两块物理盘**分别取数后相加。
    //   旧实现用 system.io：那是 netdata 对**所有**块设备的聚合，而本机 sda 上面套着 LVM
    //   （dm-0 / dm-1）=> 同一次 IO 会被 sda 与 dm-* 各记一遍，聚合值系统性偏大（重复计数）。
    //   物理盘只有 sda + nvme0n1 两块，逐盘取数（disk.sda / disk.nvme0n1 的 reads/writes）
    //   再加和，才是「磁盘读写」的真值。
    //   （system.io 仍在下面 a[4] 里取着，只用于兜底：renderSSD 取不到时由它填。）
    var io = a[4];
    state.ioFallback = io;''')

# ---------------- P4 主机卡内存条结构 ----------------
add("P4", "modify", '''            <div class="bar">
              <div class="lab"><span>内存使用率</span><b id="host-ram-txt">--</b></div>
              <div class="track"><i id="host-ram-bar" style="width:0%;background:linear-gradient(90deg,var(--accent2),var(--accent))"></i></div>
            </div>''',
'''            <div class="bar">
              <div class="lab"><span>内存使用率</span><b id="host-ram-txt">--</b></div>
              <div class="track stack">
                <i id="host-ram-bar" style="width:0%;background:linear-gradient(90deg,var(--accent2),var(--accent))"></i>
                <i id="host-ram-cache" style="width:0%;background:color-mix(in srgb, var(--dim2) 55%, transparent)"></i>
              </div>
              <div class="sub2" id="host-ram-dtl">--</div>
            </div>''')

add("P4b", "modify", '''<span><i style="background:var(--accent2)"></i>内存 %</span>''',
'''<span><i style="background:var(--accent2)"></i>内存已用 %</span>''')

# ---------------- P5 存储卡 ----------------
add("P5", "modify", '''    </div>
  </section>
</main>''',
'''    </div>
  </section>

  <!-- [v37 2026-11-05 机主「现在有两个硬盘了，我要看读、写、温度、剩余寿命」]
       两块盘的性质完全不同，必须逐盘看：
         sda      Fanxiang S100Pro 1TB（SATA SSD，系统盘，上面套 LVM）
         nvme0n1  KIOXIA EXCERIA PLUS G4 2TB（NVMe，挂 /models 与 /home）
       数据来源分两路，页面只做拼装：
         读/写  <- netdata disk.sda / disk.nvme0n1（discard 逐盘，**不用** system.io 聚合）
         温度/寿命/已写入/通电 <- 采集器经由容器内 smartctl 取（health.json 的 ssd 段） -->
  <section class="card wide" id="card-ssd">
    <div class="chead">
      <span class="badge" style="color:var(--accent2);border-color:color-mix(in srgb,var(--accent2) 50%,transparent)">STORAGE</span>
      <h2>存储</h2><span class="id" id="ssd-id"></span>
    </div>
    <div class="ssdgrid" id="ssd-rows"><div class="empty">读取中…</div></div>
  </section>
</main>''')

# ---------------- P6 renderSSD ----------------
add("P6", "modify", '''function tick(){''',
'''// --- 存储卡（v37）----------------------------------------------------------
// 两块盘的「读/写」走 netdata 逐盘图表；「温度/寿命/已写入/通电」走采集器的 SMART 段
// （health.json.ssd，60s 一刷）。两路都按「取不到 = null = 显示 -- 且不置色」处理。
// 寿命口径：NVMe = 100 - percentage_used（厂商自带磨损百分比）；
//           SATA = SMART 231/177 的 normalized VALUE（100 = 全新，厂商定义）。
//           SATA 的「已写入」**不显示数字**：属性 241 的单位随厂商而异（32MiB / LBA / 1GiB 都有），
//           本盘不在 smartctl 数据库里 => 猜一个单位就等于编数据。原始值放 title。
function rateTxt(kib){
  if (kib === null || kib === undefined || isNaN(kib)) return "--";
  return kib >= 1024 ? (fmt(kib / 1024, 1) + "<small>MiB/s</small>")
                     : (fmt(kib, 1) + "<small>KiB/s</small>");
}
function ssdDeck(){
  var d = state.ssd && state.ssd.disks ? state.ssd.disks : {};
  return [
    { key: "nvme0n1", chart: state.ids.diskNvme, tag: "NVMe", note: "数据盘 · /models /home" },
    { key: "sda",     chart: state.ids.diskSda,  tag: "SATA", note: "系统盘 · LVM root" }
  ].map(function(x){ x.meta = d[x.key] || {}; return x; });
}
function renderSSD(){
  var deck = ssdDeck();
  return Promise.all(deck.map(function(x){ return series(x.chart, 60); })).then(function(arr){
    var html = "", rdSum = 0, wrSum = 0, nIO = 0;
    deck.forEach(function(x, i){
      var s = arr[i], rd = null, wr = null;
      if (s && s.rows.length){
        var a = last(s, "reads"), b = last(s, "writes");
        rd = a === null ? null : Math.abs(a);
        wr = b === null ? null : Math.abs(b);
        if (rd !== null && wr !== null){ rdSum += rd; wrSum += wr; nIO++; }
      }
      var m = x.meta || {};
      var life = hasNum(m.life) ? m.life : null;
      var lifeLvl = life === null ? "" : (life <= 10 ? " bad" : (life <= 30 ? " warn" : " ok"));
      var tempLvl = hasNum(m.temp) ? (m.temp >= 80 ? " bad" : (m.temp >= 70 ? " warn" : "")) : "";
      var capTxt = hasNum(m.cap) ? bytes(m.cap) : "容量未知";
      var model = m.model || (x.key + "（SMART 未取到）");
      var sub = x.key + " · " + capTxt + " · " + x.tag + " · " + x.note;
      var written = hasNum(m.written) ? bytes(m.written) : "--";
      var hours = hasNum(m.hours) ? fmt(m.hours, 0) : "--";
      var wTitle = hasNum(m.written) ? "SMART 累计写入量"
        : ("本盘不显示累计写入：SMART 241 的原始值 " + (m.lba_w === undefined ? "?" : m.lba_w) +
           "，单位由厂商定义（32MiB / LBA / 1GiB 都有），本盘不在 smartctl 数据库内 => 不猜。");
      html += '<div class="ssdrow">'
        + '<div class="ssdname"><div class="t">' + model + '</div><div class="s">' + sub + '</div></div>'
        + '<div class="ssdcell"><div class="k">读</div><div class="v">' + rateTxt(rd) + '</div></div>'
        + '<div class="ssdcell"><div class="k">写</div><div class="v">' + rateTxt(wr) + '</div></div>'
        + '<div class="ssdcell ' + tempLvl + '" title="SMART 温度（' + (m.kind === "nvme" ? "Composite" : "属性 194") + '）">'
        +   '<div class="k">温度</div><div class="v">' + fmt(m.temp, 0) + '<small>°C</small></div></div>'
        + '<div class="ssdcell' + lifeLvl + '" title="寿命剩余：' + (m.kind === "nvme" ? "100 - Percentage Used" : "SMART 231/177 归一化值") + '">'
        +   '<div class="k">寿命剩余</div><div class="v">' + (life === null ? "--" : fmt(life, 0)) + '<small>%</small></div></div>'
        + '<div class="ssdcell" title="' + wTitle + '"><div class="k">已写入</div><div class="v">' + written + '</div></div>'
        + '<div class="ssdcell"><div class="k">通电</div><div class="v">' + hours + '<small>h</small></div></div>'
        + '</div>';
    });
    var rows = $("ssd-rows");
    if (rows) rows.innerHTML = html;
    // 主机卡的「磁盘读/写」= 两块物理盘之和（renderSSD 拥有这两个瓦片）
    if (nIO > 0){
      setValU("host-io-in",  fmt(rdSum, 1), "KiB/s");
      setValU("host-io-out", fmt(wrSum, 1), "KiB/s");
    } else if (state.ioFallback && state.ioFallback.rows && state.ioFallback.rows.length){
      var io = state.ioFallback;
      setValU("host-io-in",  fmt(Math.abs(last(io, "reads") || 0), 1), "KiB/s");
      setValU("host-io-out", fmt(Math.abs(last(io, "writes") || 0), 1), "KiB/s");
    }
    var sm = state.ssd && state.ssd.ts;
    setText("ssd-id", sm ? ("SMART 采集 " + Math.max(0, Math.round(Date.now() / 1000 - sm)) + "s 前 · 读写 2s")
                         : "SMART 段未取到（仅显示读写）");
  });
}

function tick(){''')

add("P6b", "modify", '''  var jobs = [renderAMD(ids, win), renderHost(ids, win), renderStatics(ids), renderNVD(ids, win),
              renderHostExtra(ids)];''',
'''  var jobs = [renderAMD(ids, win), renderHost(ids, win), renderStatics(ids), renderNVD(ids, win),
              renderHostExtra(ids), renderSSD()];''')

# ---------------- P7 ids / state ----------------
add("P7a", "modify", '''  hsTsSame: 0          // 同一个 ts 被连续读到的次数（>=2 即约 20s 没换过数据）
};''',
'''  hsTsSame: 0,         // 同一个 ts 被连续读到的次数（>=2 即约 20s 没换过数据）
  mem: null,           // [v37] /proc/meminfo 全量（health.json.mem）
  ssd: null,           // [v37] SMART 段（health.json.ssd）
  ioFallback: null     // [v37] system.io 最新系列：逐盘图表取不到时的兜底
};''')

add("P7b", "modify", '''  ids.cpuPower = pick(["cpu.powercap_intel_rapl_zone"]);''',
'''  ids.cpuPower = pick(["cpu.powercap_intel_rapl_zone"]);
  // [v37] 整机功耗要算内存域：RAPL 的 dram 子域（package-0 下面那一层）
  ids.cpuDram  = pick(["cpu.powercap_intel_rapl_subzones"]);
  // [v37] 存储卡：两块物理盘。**不能用 pick()** —— chartIndex 只索引 context
  //   （disk.io），而这两块盘共享同一个 context，pick 只会返回其中一块。
  ids.diskSda   = pickExact("disk.sda");
  ids.diskNvme  = pickExact("disk.nvme0n1");
  // [v37] 内存「已用 %」曲线用它换算（MemAvailable，与 free 的 available 同源）
  ids.memAvail = pick(["mem.available"]);''')

add("P7c", "modify", '''function pick(list){''',
'''// 按 chart id 精确取（pick() 走的是 context 索引，同一 context 下的多块盘会撞车）
function pickExact(id){
  return (state.rawCharts && state.rawCharts[id]) ? id : null;
}
function pick(list){''')

# 主机图多取一条 mem.available（追加在末尾，不动已有下标）
add("P7d", "modify", '''    series(ids.net, win), series(ids.io, win), series(ids.disk, 60)
  ]).then(function(a){''',
'''    series(ids.net, win), series(ids.io, win), series(ids.disk, 60), series(ids.memAvail, 60)
  ]).then(function(a){''')

# ---------------- P8 CPU 内存域功耗 ----------------
add("P8", "modify", '''    series(ids.cpuPower, 60), series(ids.cpuFreq, 60), series(ids.uptime, 60),
    series(ids.cpuFan, 60)
  ]).then(function(a){
    var pw = a[0];
    state.live.cpuPower = last(pw, "power");''',
'''    series(ids.cpuPower, 60), series(ids.cpuFreq, 60), series(ids.uptime, 60),
    series(ids.cpuFan, 60), series(ids.cpuDram, 60)
  ]).then(function(a){
    var pw = a[0];
    state.live.cpuPower = last(pw, "power");
    // [v37] 内存域功耗（RAPL dram 子域）。Xeon E5 v4 的 DRAM 域独立计量，
    //   在整机口径里它和 CPU 封装是两块不同的表，必须分开加 —— 只加 package 会漏掉它。
    state.live.cpuDram = last(a[4], "dram");''')

# ---------------- P9 顶栏：常驻服务归因 ----------------
add("P9a", "modify", '''function strataHold(p){
  return (p.strata_serve > 0) && (p.box_car === 0) && (p.box_ctr === 0);
}''',
'''function strataHold(p){
  // [v37 2026-11-05] 判据从「只认 ps 里字面 strata --serve」扩成两路取或：
  //   strata_serve = 命令行匹配 `strata* --serve`（含生产容器的 strata-0.1.56-090 --serve）
  //   prod_srv     = 生产包装进程 serve/server.py --engine strata
  //   实测根因：v36 只认字面形态 => 生产容器一开就漏检 => 顶栏恒显「显存泄漏 3088x」红色
  //   假警，而实际是模型常驻（33.5GB / 基线 10.9MB）。探针输出与 rc 一字未动，
  //   这里只影响**展示层归因**。
  var hold = (hasNum(p.strata_serve) && p.strata_serve > 0) ||
             (hasNum(p.prod_srv) && p.prod_srv > 0);
  return hold && (p.box_car === 0) && (p.box_ctr === 0);
}''')

add("P9b", "modify", '''      hsSet("hs-poll-verdict",
            v ? (pollLabel(v, p) + (strHold ? "·常驻服务持有" : ""))
              : (dead ? "探针失效" : "--"),
            v ? (strHold ? "warn" : (POLL_LVL[v] || "warn")) : (dead ? "bad" : ""));''',
'''      // [v37] 常驻持有时的文案不再往「显存泄漏」后面拼后缀 —— 「泄漏·常驻服务持有」
      //   读起来自相矛盾（既说漏了、又说有主）。直接换主语：
      //     VRAM_LEAK -> 「显存有主·<谁>」；VRAM_WARN -> 「显存爬升·<谁>」。
      //   档位仍取 warn：探针 VRAM_LEAK 的语义是「立即择机重启」，而持有者是常驻服务时
      //   该讨论的是「停不停服务」，不是「重启」。服务一停，本格自动回 bad（真泄漏）。
      var holdWho = (hasNum(p.prod_srv) && p.prod_srv > 0) ? "生产服务" : "strata serve";
      var vTxt = v;
      if (v && strHold && v === "VRAM_LEAK") vTxt = "显存有主·" + holdWho;
      else if (v && strHold && v === "VRAM_WARN") vTxt = "显存爬升·" + holdWho;
      else if (v) vTxt = pollLabel(v, p);
      hsSet("hs-poll-verdict",
            v ? vTxt : (dead ? "探针失效" : "--"),
            v ? (strHold ? "warn" : (POLL_LVL[v] || "warn")) : (dead ? "bad" : ""));''')

add("P9c", "modify", '''            + "但持有这块显存的不是「泄漏」而是**常驻推理服务**：ps 数到 `strata --serve` 进程（title 末尾三路计数全 0，探针的 BUSY 判据不含它），"''',
'''            + "但持有这块显存的不是「泄漏」而是**常驻推理服务**：ps 数到 strata serve 进程 "
            + (hasNum(p.strata_serve) ? p.strata_serve : "?") + " 个 / 生产包装进程 "
            + (hasNum(p.prod_srv) ? p.prod_srv : "?") + " 个（探针的 BUSY 三路判据不含它 => BOX=IDLE），"''')

add("P9d", "modify", '''      hsSet("hs-box", p.box || "--",
            p.box === "IDLE" ? "ok" : (p.box === "BUSY" ? "warn" : ""));''',
'''      // [v37] 「状态」格原先只报探针 BOX（车 / serve / 任务容器三路）。生产服务常驻时它是
      //   IDLE，而旁边判决格写着「显存有主」=> 两格读起来打架。现在把「服务在跑」明写出来：
      //   仍是 IDLE（确实没车在跑），但补 "+服务"，并在 title 里讲清 IDLE 到底指什么。
      var boxTxt = p.box || "--";
      if (strHold && boxTxt === "IDLE") boxTxt = "IDLE+服务";
      hsSet("hs-box", boxTxt,
            (p.box === "BUSY") ? "warn" : (p.box ? "ok" : ""));
      var bxEl = $("hs-box");
      if (bxEl) bxEl.title = "探针 BOX 状态：三路或判据 = 发车脚本进程 `_rk_run_car` / "
        + "vllm 类 serve 进程 `serve_27b_routeK` / 任务容器 `rk_*|*_prevdrv_*|*_kept_*`。"
        + "本格只回答「**有没有作业在跑**」，不回答「有没有服务在跑」。"
        + "实测：生产容器 strata166-407 三路都不匹配 => 它常驻时 BOX 仍是 IDLE。"
        + "所以常驻服务在跑时本格显示 IDLE+服务（探针原值 IDLE 不变）。"
        + "三路计数：" + busyDtl(p) + "；GPU 利用率 " + busyPct(p) + "。";''')

add("P9e", "modify", '''      hsSet("hs-swap", hasNum(s.swap_used) ? bytes(s.swap_used) : "--",
            hasNum(s.swap_used) ? (s.swap_used > 0 ? "warn" : "ok") : "");''',
'''      // [v37] 判据从「>0 即橙」改成「> max(256 MiB, 1% 总量)」。
      //   实测反例：SWAP 已用 52 KiB / 总量 16 GiB（=0.0003%）也点橙 —— 颜色与量级脱钩，
      //   长期常亮就是噪声，久了会让人对整条状态栏的橙失去反应。
      //   保留原意（这机器不该真的用到 swap）：真被换出到百 MiB 量级才预警。
      var swTot = hasNum(s.swap_total) ? s.swap_total : 0;
      var swTh  = Math.max(256 * 1048576, swTot * 0.01);
      var swLvl = !hasNum(s.swap_used) ? ""
                : ((swTot > 0 && s.swap_used > swTh) ? "warn" : "ok");
      hsSet("hs-swap", hasNum(s.swap_used) ? bytes(s.swap_used) : "--", swLvl);''')

add("P9f", "modify", '''      if (swEl) swEl.title = "SWAP 已用（free -b）。判档**绝对量**（本机裁定，非百分比）："
        + ">0 即预警（橙）、=0 绿、取不到灰。16GB swap 占用 <1% 也点橙 —— 这是有意的："
        + "这台机的口径是「不该用到 swap」，一旦沾上就值得看一眼是谁被换出。";''',
'''      if (swEl) swEl.title = "SWAP 已用（free -b，容器 --pid host 读宿主量）。"
        + "判档：> max(256 MiB, 总量 1%) 才橙，其余绿，取不到灰。"
        + "原口径是「>0 即橙」—— 实测 52 KiB / 16 GiB 也常亮橙，颜色与量级脱钩，"
        + "长期噪声会稀释整条状态栏的警报价值，故收紧到「真被换出到百 MiB 级」才预警。"
        + "本机总量：" + btol(s.swap_total) + "。";''')

# ---------------- P10 renderHealth 收字段 ----------------
add("P10a", "modify", '''      var z = j.z0 || {}, p = j.poll || {}, s = j.sys || {}, bt = j.boot || {}, tg = j.tgt || {};''',
'''      var z = j.z0 || {}, p = j.poll || {}, s = j.sys || {}, bt = j.boot || {}, tg = j.tgt || {};
      // [v37] 内存全量与 SSD SMART：交给 renderHost / renderSSD 消费
      state.mem = j.mem || null;
      state.ssd = j.ssd || null;''')

# btol 小工具
add("P10b", "modify", '''function bytes(b){''',
'''// 字节数转可读串，null 安全（给 title 文案用；与 bytes() 同口径但容忍缺值）
function btol(b){ return hasNum(b) ? bytes(b) : "未知"; }
function bytes(b){''')

# ---------------- P11 CSS ----------------
add("P11", "modify", '''  .kpi.bad .v{color:var(--bad)}''',
'''  .kpi.bad .v{color:var(--bad)}
  /* --- [v37] 内存堆叠条：已用 + 缓存 --- */
  .track.stack{display:flex}
  .track.stack > i{flex:0 0 auto;min-width:0}
  .sub2{font-size:10.5px;color:var(--dim2);font-family:var(--mono);margin-top:6px;
        white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  /* --- [v37] 存储卡：名称列 + 6 个指标列 --- */
  .ssdgrid{display:grid;gap:0;flex:1 1 auto;align-content:start}
  .ssdrow{display:grid;grid-template-columns:minmax(190px,1.6fr) repeat(6,minmax(0,1fr));
          gap:20px;align-items:center;padding:16px 0}
  .ssdrow + .ssdrow{border-top:1px solid var(--line)}
  .ssdname{min-width:0}
  .ssdname .t{font-size:13px;font-weight:600;letter-spacing:-.01em;white-space:nowrap;
              overflow:hidden;text-overflow:ellipsis}
  .ssdname .s{font-size:10.5px;color:var(--dim2);font-family:var(--mono);margin-top:5px;
              white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .ssdcell{min-width:0}
  .ssdcell .k{font-size:11px;color:var(--dim2);margin-bottom:5px;white-space:nowrap}
  .ssdcell .v{font-family:var(--mono);font-size:18px;font-weight:600;font-variant-numeric:tabular-nums;
              letter-spacing:-.03em;white-space:nowrap}
  .ssdcell .v small{font-size:10.5px;color:var(--dim2);font-weight:400;margin-left:3px;letter-spacing:0}
  .ssdcell.warn .v{color:var(--warn)}
  .ssdcell.bad .v{color:var(--bad)}
  @media (max-width:980px){
    .ssdrow{grid-template-columns:repeat(3,minmax(0,1fr));gap:14px 18px}
    .ssdname{grid-column:1 / -1}
  }''')

# ---------------- apply ----------------
for tag, kind, old, new in P:
    n = s.count(old)
    assert n == 1, "%s OLD 命中 %d 次（应为 1）: %r" % (tag, n, old[:70])
    s = s.replace(old, new)
    if kind == "insert":
        for line in old.split("\n"):
            if line.strip():
                assert line.strip() in s, "%s 超集判据失败：丢了 %r" % (tag, line[:70])

out = s.replace("\n", "\r\n").encode("utf-8")
io.open(DST, "wb").write(out)
back = io.open(DST, "rb").read().decode("utf-8")
for tag, _, _, new in P:
    head = new.split("\n")[0].strip()
    assert head in back, "%s 写盘校验失败: %r" % (tag, head[:60])
print("OK %s  %d -> %d bytes  CRLF=%d  md5=%s" % (DST, len(raw), len(out), back.count("\r\n"),
      hashlib.md5(out).hexdigest()))
