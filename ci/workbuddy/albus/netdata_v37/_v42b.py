# -*- coding: utf-8 -*-
"""v42b：主机左半填实（把「负载」从总览挪进主机卡）。
理由：总览是"整机/GPU"记分板，负载是主机指标；挪过去后主机左半
(环104 + 负载行48 + 图112) 正好填满 359 的卡，不再有一大片空白。
"""
import io, hashlib, re

P = r"D:/workbuddy_space/strata_ws/albus/netdata_v37/gpu.html"
s = io.open(P, "rb").read().decode("utf-8")
crlf = "\r\n" in s
s = s.replace("\r\n", "\n")


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:70])
    s = s.replace(a, b)


# 1) 总览去掉负载格
m = re.search(r'\n      <div class="kpi" id="ov-k-load">.*?\n      </div>\n', s, re.S)
assert m, "ov-k-load 未找到"
s = s[:m.start()] + "\n" + s[m.end():]

# 2) 总览 5 等分
rep("  .kpis{display:grid;grid-template-columns:repeat(6,minmax(0,1fr))}",
    "  .kpis{display:grid;grid-template-columns:repeat(5,minmax(0,1fr))}")

# 3) 主机左半：环+内存 之后加「负载」行
rep("""          <!-- CPU 条与环内数字同源，保留节点供 JS 写入但不显示 -->
          <div class="bar" hidden><div class="track"><i id="host-cpu-bar" style="width:0%"></i></div></div>
        </div>""",
    """          <!-- CPU 条与环内数字同源，保留节点供 JS 写入但不显示 -->
          <div class="bar" hidden><div class="track"><i id="host-cpu-bar" style="width:0%"></i></div></div>
        </div>
        <div class="hload">
          <span>1 分钟<b id="host-load1">--</b></span>
          <span>5 分钟<b id="host-load5">--</b></span>
          <span>15 分钟<b id="host-load15">--</b></span>
        </div>""")

# 4) 负载行样式（与瓦片同族：10px 标签 + 15px 等宽数值）
rep("  .hram .lab{display:flex;align-items:baseline;gap:10px;font-size:var(--fs-1);",
    """  .hload{display:flex;align-items:baseline;gap:26px;margin-top:14px;padding-top:12px;
         border-top:1px solid var(--line);flex:0 0 auto}
  .hload span{font-size:10px;color:var(--dim2);letter-spacing:.02em;display:flex;
              align-items:baseline;gap:8px}
  .hload b{font-family:var(--mono);font-size:15px;font-weight:600;color:var(--text);
           letter-spacing:-.02em;font-variant-numeric:tabular-nums}
  .hram .lab{display:flex;align-items:baseline;gap:10px;font-size:var(--fs-1);""")

# 5) JS：把 load 写进主机卡（总览那两个 id 已删，setText 对 null 安全）
rep('setText("ov-load", fmt(L.load1, 2));',
    'setText("host-load1", fmt(L.load1, 2));\n  setText("host-load5", fmt(L.load5, 2));\n  setText("host-load15", fmt(L.load15, 2));')
rep('setText("ov-load-sub", (hasNum(L.load1) && state.cores) ? ("每核 " + fmt(L.load1 / state.cores, 2)) : "");',
    '')

if crlf:
    s = s.replace("\n", "\r\n")
io.open(P, "wb").write(s.encode("utf-8"))
print("OK", len(s.encode("utf-8")), hashlib.md5(s.encode("utf-8")).hexdigest())
