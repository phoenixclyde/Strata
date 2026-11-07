# -*- coding: utf-8 -*-
"""v37b 补丁（页面）：把内存堆叠条改成分母自洽的三段，并把「已写入」改成十进制 GB。
现场证据（2026-11-05 00:55，宿主 /proc/meminfo）：
  MemTotal 125.7 GiB / MemFree 1.5 / MemAvailable 16.0 / Cached 43.9 / Unevictable 26.8(mLocked)
  => 「缓存 43.9 GiB」里约 26.8 GiB 是 mlocked（不可回收、已计入 used），
     直接把它画成「已用之外的另一段」= 重复计数（条会被 100% 截断）。
  自洽分解（三段刚好加满 total）：
     已用   = total - available      （不可回收，= `free` 3.3.17+ 的 used）
     可回收 = available - free       （真能腾出来的页缓存）
     空闲   = free
"""
import io, hashlib

P = r"D:/workbuddy_space/strata_ws/albus/netdata_v37/gpu.html"
s = io.open(P, "rb").read().decode("utf-8")
assert "\r\n" in s

pairs = []

old1 = '''      var mUsed = Math.max(0, M.total - M.available);
      var mCache = Math.max(0, (M.cached || 0) + (M.buffers || 0) + (M.sreclaim || 0));
      var upct = mUsed / M.total * 100;
      setText("host-ram-txt", bytes(mUsed) + " / " + bytes(M.total) + "  (" + fmt(upct, 1) + "%)");
      setWidth("host-ram-bar", upct);
      setWidth("host-ram-cache", Math.min(100 - upct, mCache / M.total * 100));
      setText("host-ram-dtl", "缓存 " + bytes(mCache) + "（可回收） · 可用 " + bytes(M.available));
      state.live.ramUsedB = mUsed;
      state.live.ramTotalB = M.total;
      state.live.ramPct = upct;
      state.live.ramCacheB = mCache;'''
new1 = '''      var mUsed = Math.max(0, M.total - M.available);
      var mFree = hasNum(M.free) ? Math.max(0, M.free) : 0;
      // [v37b 实测校正] 第二段只能是「**可回收**缓存」，不能是整个 Cached：
      //   本机 Cached 43.9 GiB 里有 ~26.8 GiB 是 mlocked（Unevictable），那部分
      //   **已经算在 used 里**（所以 available 只有 16 GiB 而不是 free+cache）。把它
      //   再画一段 => 重复计数、条被 100% 截断（第一版就这么错了，截图看出来才发现）。
      var mRecl = Math.max(0, M.available - mFree);
      var upct = mUsed / M.total * 100;
      setText("host-ram-txt", bytes(mUsed) + " / " + bytes(M.total) + "  (" + fmt(upct, 1) + "%)");
      setWidth("host-ram-bar", upct);
      setWidth("host-ram-cache", mRecl / M.total * 100);
      setText("host-ram-dtl", "可回收 " + bytes(mRecl) + " · 空闲 " + bytes(mFree) +
        (hasNum(M.unevict) && M.unevict > 0 ? (" · 锁定 " + bytes(M.unevict) + "（已计入已用）") : ""));
      state.live.ramUsedB = mUsed;
      state.live.ramTotalB = M.total;
      state.live.ramPct = upct;
      state.live.ramReclB = mRecl;
      var rEl = $("host-ram-bar");
      if (rEl && rEl.parentNode && rEl.parentNode.parentNode){
        var barEl = rEl.parentNode.parentNode;
        barEl.title = "三段自洽相加 = 物理内存总量：" +
          "已用 " + bytes(mUsed) + "（= total − MemAvailable，不可回收）" +
          " + 可回收 " + bytes(mRecl) + "（MemAvailable − MemFree，页缓存里真能被回收的部分）" +
          " + 空闲 " + bytes(mFree) + "。"
          + "口径说明：现代 `free`(3.3.17+) 的 used 就是 total − available，与本行一致；"
          + "旧的 used = total − free − cache 会把 mlocked 缓存算成「空闲」。"
          + (hasNum(M.unevict) ? "本机 Unevictable(Mlocked) " + bytes(M.unevict) + "，属不可回收缓存，已计入已用。" : "");
      }'''
pairs.append(("Q1", old1, new1))

old2 = '''      setWidth("host-ram-cache", 0);
      setText("host-ram-dtl", "缓存明细不可用（采集器 mem 缺失，口径为 system.ram 四维）");'''
new2 = '''      setWidth("host-ram-cache", 0);
      setText("host-ram-dtl", "明细不可用（采集器 mem 段缺失，退回 system.ram 四维口径）");'''
pairs.append(("Q2", old2, new2))

# 已写入：十进制 GB（与 smartctl 的 [606 GB] 对齐，避免 GiB/GB 两个口径混用）
old3 = '''      var written = hasNum(m.written) ? bytes(m.written) : "--";'''
new3 = '''      // [v37b] 用十进制 GB：smartctl 报的是 GB（1e9），页面其它地方用 GiB（2^30）。
      //   同一个数两种单位并排会被读成"对不上"（606 GB vs 564.6 GiB），这里统一成 GB 并标注。
      var written = hasNum(m.written) ? (fmt(m.written / 1e9, 1) + "<small>GB</small>") : "--";'''
pairs.append(("Q3", old3, new3))

# 主机卡磁盘读/写瓦片加 title，说明是两块物理盘之和
old4 = '''          <div class="tile"><div class="k">磁盘读</div><div class="v" id="host-io-in">--<small>KiB/s</small></div></div>
          <div class="tile"><div class="k">磁盘写</div><div class="v" id="host-io-out">--<small>KiB/s</small></div></div>'''
new4 = '''          <div class="tile" title="两块物理盘（sda + nvme0n1）逐盘取数后相加；不用 system.io 聚合 —— 本机 sda 上套着 LVM，dm-* 会把同一次 IO 重复计一遍"><div class="k">磁盘读</div><div class="v" id="host-io-in">--<small>KiB/s</small></div></div>
          <div class="tile" title="两块物理盘（sda + nvme0n1）逐盘取数后相加；不用 system.io 聚合 —— 本机 sda 上套着 LVM，dm-* 会把同一次 IO 重复计一遍"><div class="k">磁盘写</div><div class="v" id="host-io-out">--<small>KiB/s</small></div></div>'''
pairs.append(("Q4", old4, new4))

for tag, old, new in pairs:
    n = s.count(old.replace("\n", "\r\n"))
    assert n == 1, "%s 命中 %d 次" % (tag, n)
    s = s.replace(old.replace("\n", "\r\n"), new.replace("\n", "\r\n"))

io.open(P, "wb").write(s.encode("utf-8"))
back = io.open(P, "rb").read().decode("utf-8")
for tag, _, new in pairs:
    assert new.split("\n")[0].strip() in back, tag
print("OK", len(back.encode()), hashlib.md5(back.encode()).hexdigest(), "CRLF", back.count("\r\n"))
