# -*- coding: utf-8 -*-
"""v37c：SSD 健康位（Critical Warning / Available Spare vs Threshold）。
依据（NVMe 规范 + smartmontools 文档，2026-11-05 查证）：
  Percentage Used 只是「厂商估算的已耗耐久度」，100 也**不代表故障**；
  真正的故障信号是 Critical Warning 非 0、Available Spare 低于该盘自报阈值、Media Errors 增长。
=> 寿命格不能独自承担「健康」语义，得把这三个判据补上，否则「100%」会让人误以为万无一失。
"""
import io, hashlib

C = r"D:/workbuddy_space/strata_ws/albus/netdata_v37/rk-health-collect.sh"
s = io.open(C, encoding="utf-8").read()
old = '''        out["spare"] = h.get("available_spare")'''
new = '''        out["spare"] = h.get("available_spare")
        # [v37c] 备用空间阈值：健康判据是「spare < 该盘自报阈值」，
        #   阈值随盘而异（不是统一 10%），必须整盘读取而不是拿常量比。
        out["spare_th"] = h.get("available_spare_threshold")'''
assert s.count(old) == 1, s.count(old)
s = s.replace(old, new)
io.open(C, "w", encoding="utf-8", newline="\n").write(s)
print("collector OK", len(s.encode()), hashlib.md5(s.encode()).hexdigest())

P = r"D:/workbuddy_space/strata_ws/albus/netdata_v37/gpu.html"
p = io.open(P, "rb").read().decode("utf-8")
pairs = []

old1 = '''      var capTxt = hasNum(m.cap) ? bytes(m.cap) : "容量未知";
      var model = m.model || (x.key + "（SMART 未取到）");
      var sub = x.key + " · " + capTxt + " · " + x.tag + " · " + x.note;'''
new1 = '''      var capTxt = hasNum(m.cap) ? bytes(m.cap) : "容量未知";
      var model = m.model || (x.key + "（SMART 未取到）");
      // [v37c] 健康位：**寿命不是健康**（NVMe 规范：Percentage Used=100 也只是「额定耐久度用完」，
      //   不必然故障）。真正的故障信号是 Critical Warning 非 0、Available Spare 低于该盘阈值、
      //   Media Errors 增长。这里三判据合成一个徽章，取不到就显示「?」不置色。
      var hOk = null;
      if (hasNum(m.ok)){
        var crit = hasNum(m.crit) ? m.crit : 0;
        var spareLow = hasNum(m.spare) && hasNum(m.spare_th) && m.spare < m.spare_th;
        var media = hasNum(m.media_err) ? m.media_err : 0;
        hOk = (m.ok === 1) && crit === 0 && !spareLow && media === 0;
      }
      var hTxt = hOk === null ? "SMART ?" : (hOk ? "SMART 正常" : "SMART 告警");
      var hCls = hOk === null ? "h?" : (hOk ? "hok" : "hbad");
      var sub = x.key + " · " + capTxt + " · " + x.tag + " · " + x.note
        + ' · <b class="' + hCls + '">' + hTxt + "</b>";'''
pairs.append(("H1", old1, new1))

old2 = '''        + '<div class="ssdcell' + lifeLvl + '" title="寿命剩余：' + (m.kind === "nvme" ? "100 - Percentage Used" : "SMART 231/177 归一化值") + '">'
        +   '<div class="k">寿命剩余</div><div class="v">' + (life === null ? "--" : fmt(life, 0)) + '<small>%</small></div></div>\''''
new2 = '''        + '<div class="ssdcell' + lifeLvl + '" title="寿命剩余：' + (m.kind === "nvme" ? "100 - Percentage Used（厂商估算的已耗耐久度）" : "SMART 231/177 归一化值") + '。'
        +   '注意：**耐久度不等于健康** —— 100 表示额定写入寿命用完，不代表盘坏了；'
        +   '真正的故障信号是 Critical Warning 非 0 / Available Spare 低于该盘阈值 / 校验错误增长。'
        +   (m.kind === "nvme" ? ("本盘：Percentage Used=" + (hasNum(m.life) ? (100 - m.life) : "?") + "%"
            + "，Available Spare=" + (hasNum(m.spare) ? m.spare + "%" : "?")
            + "（阈值 " + (hasNum(m.spare_th) ? m.spare_th + "%" : "?") + "）"
            + "，Critical Warning=" + (hasNum(m.crit) ? "0x0" + m.crit : "?")
            + "，Media Errors=" + (hasNum(m.media_err) ? m.media_err : "?")) : "")
        + '">'
        +   '<div class="k">寿命剩余</div><div class="v">' + (life === null ? "--" : fmt(life, 0)) + '<small>%</small></div></div>\''''
pairs.append(("H2", old2, new2))

# 徽章配色
old3 = '''  .ssdcell.warn .v{color:var(--warn)}'''
new3 = '''  .ssdcell.warn .v{color:var(--warn)}
  .ssdname .s b.hok{color:var(--good);font-weight:600}
  .ssdname .s b.hbad{color:var(--bad);font-weight:600}
  .ssdname .s b.h\\?{color:var(--dim);font-weight:400}'''
pairs.append(("H3", old3, new3))

for tag, old, new in pairs:
    n = p.count(old.replace("\n", "\r\n"))
    assert n == 1, "%s 命中 %d" % (tag, n)
    p = p.replace(old.replace("\n", "\r\n"), new.replace("\n", "\r\n"))

io.open(P, "wb").write(p.encode("utf-8"))
print("page OK", len(p.encode()), hashlib.md5(p.encode()).hexdigest())
