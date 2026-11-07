# -*- coding: utf-8 -*-
"""v50：回滚记分板的括号（上一版误解了），改成磁盘卡「容量占用」后面带 (已用 / 总量)。"""
import io, hashlib

P = r"D:/workbuddy_space/strata_ws/albus/netdata_v37/gpu.html"
s = io.open(P, "rb").read().decode("utf-8")
crlf = "\r\n" in s
s = s.replace("\r\n", "\n")


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:70])
    s = s.replace(a, b)


# ---------- 回滚 1/3：显存 ----------
rep('''  setKpi("ov-vram", fmt(vPct, 1), "%");
  (function(){ var e = $("ov-vram");
    if (e && vTot) e.innerHTML += '<em>(' + fmt(vUsed / 1073741824, 1) + " / "
      + fmt(vTot / 1073741824, 1) + ' GiB)</em>'; })();''',
    '''  setKpi("ov-vram", fmt(vPct, 1), "%");''')

# ---------- 回滚 2/3：内存 ----------
rep('''  setKpi("ov-ram", fmt(L.ramPct, 1), "%");
  (function(){ var e = $("ov-ram");
    if (e && hasNum(L.ramTotalB) && L.ramTotalB > 0) e.innerHTML += '<em>('
      + fmt(L.ramUsedB / 1073741824, 1) + " / " + fmt(L.ramTotalB / 1073741824, 1)
      + ' GiB)</em>'; })();''',
    '''  setKpi("ov-ram", fmt(L.ramPct, 1), "%");''')

# ---------- 回滚 3/3：CPU ----------
rep('''  setKpi("ov-cpu", fmt(L.cpuPct, 1), "%");
  (function(){ var e = $("ov-cpu");
    if (e && hasNum(L.cpuPct) && state.cores) e.innerHTML += '<em>('
      + fmt(L.cpuPct * state.cores / 100, 1) + " / " + state.cores + ' 线程)</em>'; })();''',
    '''  setKpi("ov-cpu", fmt(L.cpuPct, 1), "%");''')

# ---------- 回滚副标题 ----------
rep('''  setText("ov-vram-sub", vTot ? ("空闲 " + bytes(Math.max(0, vTot - vUsed))) : "无数据");''',
    '''  setText("ov-vram-sub", vTot ? (bytes(vUsed) + " / " + bytes(vTot)) : "无数据");''')
rep('''  setText("ov-ram-sub", (hasNum(L.ramTotalB) && L.ramTotalB > 0)
    ? ("余量 " + bytes(Math.max(0, L.ramTotalB - L.ramUsedB)) + "（含缓存）") : "");''',
    '''  setText("ov-ram-sub", (hasNum(L.ramTotalB) && L.ramTotalB > 0)
    ? (bytes(L.ramUsedB) + " / " + bytes(L.ramTotalB)) : "");''')

# ---------- 正题：磁盘卡容量占用补括号 ----------
rep('''      var capTxt = usedPct === null ? "--" : fmt(usedPct, 1) + "%";''',
    '''      var capTxt = usedPct === null ? "--" : fmt(usedPct, 1) + "%";
      // 括号里两个数由「本盘物理容量 × 该百分比」推出，与左边百分数必然自洽
      var capGiB  = hasNum(m.cap) ? m.cap / 1073741824 : null;
      var capPair = (capGiB !== null && usedPct !== null)
        ? "(" + fmt(capGiB * usedPct / 100, 0) + " / " + fmt(capGiB, 0) + " GiB)" : "";''')

OLD = """        +   '<div class="cap"><span>容量占用</span><b>' + capTxt + '</b></div>'"""
NEW = """        +   '<div class="cap"><span>容量占用</span><b>' + capTxt
        +     (capPair ? '<em>' + capPair + '</em>' : '') + '</b></div>'
"""
rep(OLD, NEW)

rep("""  .kpi .v em{font-style:normal;font-family:var(--font);font-size:12px;font-weight:400;
             color:var(--dim2);margin-left:8px;letter-spacing:0;white-space:nowrap}""",
    """  .kpi .v em, .dcap .cap b em{font-style:normal;font-family:var(--font);font-size:12px;
             font-weight:400;color:var(--dim2);margin-left:7px;letter-spacing:0;white-space:nowrap}""")

if crlf:
    s = s.replace("\n", "\r\n")
io.open(P, "wb").write(s.encode("utf-8"))
print("OK", len(s.encode("utf-8")), hashlib.md5(s.encode("utf-8")).hexdigest())
