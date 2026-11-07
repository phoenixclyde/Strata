# -*- coding: utf-8 -*-
"""v40：整体重写 <style>。保留头部主题 token（配色有据可查），
把 v37~v39 三层叠加的版式规则全部推倒，换成单一尺度、单层规则。
脚本只做「切出 style 前半段 + 拼新后半段」，不动 body 与 JS。"""
import io, hashlib, os

P = r"D:/workbuddy_space/strata_ws/albus/netdata_v37/gpu.html"
s = io.open(P, "rb").read().decode("utf-8")
crlf = "\r\n" in s
s = s.replace("\r\n", "\n")

MARK = "  /* --- 顶栏（吸顶玻璃条）--- */"
i = s.find(MARK)
assert i > 0, "找不到切分点"
j = s.find("</style>", i)
assert j > i

HEAD = s[:i]
TAIL = s[j:]

CSS = r"""  /* ==========================================================================
     v40 版式（2026-11-05 整体重写）
     为什么重写：v37/v38/v39 是三层补丁，同名选择器在不同段落里各定义一次
     （.hostgrid 3 次、.tiles 5 次、.drow 3 次、.kpi 4 次），特异性相同靠顺序取胜，
     改一处就被后面覆盖 —— 表现就是「对齐时好时坏、字号时大时小」。
     现在：一个尺度、一层规则、每个选择器只出现一次。

     尺度（全部 4 的倍数）：
       间距 4 / 8 / 12 / 14 / 16 / 20 / 22 / 24      字号 7 档（见 --fs-*）
     栅格：
       header  通栏
       记分板   6 等分，竖发丝线分隔
       显卡    1fr 1fr（同构：128 环 + 4×2 瓦片 + 图）
       主机    212 | 1fr | 1.02fr（竖发丝线分隔；三栏顶对齐）
     ========================================================================== */

  :root{
    --fs-1:11px;    /* 标签 / 图例 / 元信息 */
    --fs-2:12px;    /* 次值 / 说明 */
    --fs-3:15px;    /* 行内主值 */
    --fs-4:22px;    /* 瓦片 */
    --fs-5:28px;    /* 记分板 */
    --fs-6:38px;    /* 环形 / 主机主值 */
    --line-soft:color-mix(in srgb, var(--line) 55%, transparent);
    --tile-bg:color-mix(in srgb, var(--text) 3.5%, transparent);
  }

  *{box-sizing:border-box}
  html,body{margin:0;padding:0}
  html{overflow-x:auto;scroll-behavior:smooth}
  body{
    display:flex;flex-direction:column;min-height:100vh;
    padding:14px 20px 12px;
    background-color:var(--bg);
    background-image:linear-gradient(180deg, var(--bg2) 0%, var(--bg) 38%);
    color:var(--text);font-family:var(--font);font-size:14px;
    -webkit-font-smoothing:antialiased;
  }
  a{color:var(--accent);text-decoration:none}
  ::selection{background:color-mix(in srgb, var(--accent) 32%, transparent)}
  ::-webkit-scrollbar{width:11px;height:11px}
  ::-webkit-scrollbar-track{background:transparent}
  ::-webkit-scrollbar-thumb{background:color-mix(in srgb, var(--text) 15%, transparent);
    border-radius:99px;border:3px solid transparent;background-clip:content-box}
  ::-webkit-scrollbar-thumb:hover{background:color-mix(in srgb, var(--text) 26%, transparent);background-clip:content-box}
  .fillarea{opacity:var(--fill,.42)}

  /* ---------- 顶栏 ---------- */
  header{
    flex:0 0 auto;margin-bottom:var(--gap);padding:12px 20px;
    background:linear-gradient(180deg, color-mix(in srgb, var(--panel2) 45%, var(--panel)) 0%, var(--panel) 100%);
    border:1px solid var(--line);border-radius:var(--radius);
    box-shadow:var(--hairline), var(--shadow);
  }
  .hrow{display:flex;flex-wrap:wrap;align-items:center;gap:10px 14px}
  .brand{display:flex;align-items:baseline;gap:10px}
  .brand h1{font-size:17px;margin:0;font-weight:600;letter-spacing:-.01em}
  .brand .sub{color:var(--dim);font-size:var(--fs-2);font-family:var(--mono)}
  .spacer{flex:1 1 auto}
  .chip{
    display:inline-flex;align-items:center;gap:7px;padding:4px 11px;border-radius:999px;
    background:color-mix(in srgb, var(--text) 4%, transparent);
    border:1px solid var(--line);color:var(--dim);font-size:var(--fs-2);font-family:var(--mono);
  }
  .dot{width:6px;height:6px;border-radius:50%;background:var(--good);
       box-shadow:0 0 0 3px color-mix(in srgb, var(--good) 14%, transparent);
       animation:pulse 2.6s var(--ease) infinite}
  .dot.bad{background:var(--bad);box-shadow:0 0 0 3px color-mix(in srgb, var(--bad) 18%, transparent), 0 0 10px var(--bad)}
  @keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.5;transform:scale(.82)}}
  .seg{display:inline-flex;border:1px solid var(--line);border-radius:8px;overflow:hidden;
       background:color-mix(in srgb, var(--text) 4%, transparent)}
  .seg button{
    background:transparent;border:0;color:var(--dim);padding:5px 10px;cursor:pointer;
    font-family:var(--font);font-size:var(--fs-2);border-right:1px solid var(--line);
    transition:color .16s, background .16s;
  }
  .seg button:last-child{border-right:0}
  .seg button:hover{color:var(--text);background:color-mix(in srgb, var(--text) 6%, transparent)}
  .seg button.on{background:color-mix(in srgb, var(--accent) 20%, transparent);color:var(--text)}

  /* ---------- 顶栏状态组（23 格 / 4 组） ---------- */
  .hstat{display:flex;flex-wrap:wrap;align-items:center;gap:8px 26px;
         margin-top:11px;padding-top:11px;border-top:1px solid var(--line)}
  .hsg{display:inline-flex;flex-wrap:wrap;align-items:center;gap:6px 14px;min-width:0}
  .hsg > .hsl{font-family:var(--mono);font-size:10px;letter-spacing:.14em;color:var(--dim2);
              padding:2px 6px;border-radius:4px;background:color-mix(in srgb, var(--text) 7%, transparent)}
  .hsi{display:inline-flex;align-items:center;gap:6px;font-size:var(--fs-1);color:var(--dim2);white-space:nowrap}
  .hsi i{width:5px;height:5px;border-radius:50%;background:var(--dim2);flex:0 0 auto}
  .hsi b{font-family:var(--mono);font-size:var(--fs-2);font-weight:600;color:var(--text);letter-spacing:0}
  .hsi.ok i{background:var(--good)}
  .hsi.warn i{background:var(--warn)}  .hsi.warn b{color:var(--warn)}
  .hsi.bad i{background:var(--bad)}    .hsi.bad b{color:var(--bad)}
  .hsi.defer i{background:transparent;box-shadow:inset 0 0 0 1.5px var(--warn)}
  .hsi.defer b{color:var(--text)}
  .hsi.busy b{font-size:13px;font-weight:700;color:var(--warn);letter-spacing:.02em}

  /* ---------- 主体栅格 ---------- */
  header,main,footer{width:100%;position:relative;z-index:1;flex:0 0 auto}
  main{
    flex:1 1 auto;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));
    gap:var(--gap);
    /* 行 1 记分板按内容；行 2/3 按比例吃掉剩余高度（图区吸收），
       下限用 min-content —— 屏幕太矮时退回内容高度并允许纵向滚动，不压坏内容 */
    grid-template-rows:auto minmax(min-content,1.34fr) minmax(min-content,1fr);
  }
  @keyframes rise{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
  main > .card{animation:rise .5s var(--ease) backwards}
  main > .card:nth-child(1){animation-delay:.02s}
  main > .card:nth-child(2){animation-delay:.06s}
  main > .card:nth-child(3){animation-delay:.1s}
  main > .card:nth-child(4){animation-delay:.14s}
  @media (prefers-reduced-motion: reduce){
    main > .card{animation:none}
    .dot{animation:none}
    *{transition-duration:.01ms !important}
  }

  /* ---------- 卡片 ---------- */
  .card{
    position:relative;overflow:hidden;display:flex;flex-direction:column;min-height:0;
    padding:16px 20px;
    background:linear-gradient(180deg, color-mix(in srgb, var(--panel2) 40%, var(--panel)) 0%, var(--panel) 60%);
    border:1px solid var(--line);border-radius:var(--radius);
    box-shadow:var(--hairline), var(--shadow);
  }
  .card.wide{grid-column:1/-1}
  .chead{display:flex;align-items:center;gap:10px;height:24px;margin-bottom:14px;flex:0 0 auto}
  .chead .badge{
    font-family:var(--mono);font-size:10px;letter-spacing:.12em;padding:3px 7px;border-radius:4px;
    color:var(--dim);background:color-mix(in srgb, currentColor 15%, transparent);
  }
  .chead h2{font-size:var(--fs-3);margin:0;font-weight:600;letter-spacing:.01em}
  .chead .id{margin-left:auto;color:var(--dim2);font-family:var(--mono);font-size:var(--fs-1)}

  /* ---------- 环形 ---------- */
  .top{display:grid;grid-template-columns:128px minmax(0,1fr);gap:20px;align-items:center;flex:0 0 auto}
  #nvd-body{display:flex;flex-direction:column;min-height:0;flex:1 1 auto}
  .ring{position:relative;width:128px;height:128px}
  .ring svg{display:block;transform:rotate(-90deg);width:100%;height:100%}
  #amd-ring,#nvd-ring,#host-ring{transition:stroke-dashoffset .65s var(--ease)}
  .ring .val{position:absolute;inset:0;display:flex;flex-direction:column;
             align-items:center;justify-content:center;font-family:var(--mono)}
  .ring .val b{font-size:var(--fs-6);font-weight:600;line-height:1;letter-spacing:-.04em;
               font-variant-numeric:tabular-nums}
  .ring .val span{font-size:10px;color:var(--dim2);margin-top:6px;letter-spacing:.14em}

  /* ---------- 进度条 ---------- */
  .bar{margin:0}
  .bar .lab{display:flex;justify-content:space-between;align-items:baseline;
            font-size:var(--fs-1);color:var(--dim2);margin-bottom:6px;letter-spacing:.02em}
  .bar .lab b{font-family:var(--mono);font-size:var(--fs-2);font-weight:600;color:var(--text);
              letter-spacing:-.01em;font-variant-numeric:tabular-nums}
  .track{height:4px;border-radius:99px;background:var(--grid);overflow:hidden}
  .track > i{display:block;height:100%;border-radius:99px;transition:width .45s var(--ease)}
  .track.stack{display:flex}
  .track.stack > i{flex:0 0 auto;min-width:0}
  .sub2{font-size:var(--fs-1);color:var(--dim2);font-family:var(--mono);
        margin-top:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}

  /* ---------- 瓦片：给每个数字一个底，4 列固定 ---------- */
  .tiles{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));
         grid-auto-rows:58px;gap:8px;margin-top:12px}
  .tile{min-width:0;padding:8px 10px;border-radius:8px;
        background:var(--tile-bg);border:1px solid var(--line-soft);
        display:flex;flex-direction:column;justify-content:center;
        transition:background .18s var(--ease)}
  .tile:hover{background:color-mix(in srgb, var(--text) 6%, transparent)}
  .tile .k{font-size:var(--fs-1);color:var(--dim2);margin-bottom:4px;letter-spacing:.02em;
           white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .tile .v{font-family:var(--mono);font-size:var(--fs-4);font-weight:600;line-height:1.1;
           letter-spacing:-.03em;font-variant-numeric:tabular-nums;white-space:nowrap}
  .tile .v small{font-size:var(--fs-1);font-weight:400;color:var(--dim2);margin-left:3px;letter-spacing:0}

  /* ---------- 图表 ---------- */
  svg text{font-family:var(--mono);font-variant-numeric:tabular-nums}
  /* flex:1 1 0 + height:0：高度完全由剩余空间决定，且**测量时就是最终值**，
     不会出现「先按 viewBox 比例撑高 155px、再把文字拉成长条」（v38 踩过）。
     任何残留瞬时形变都会被下一轮 2s tick 的重新测量纠正。 */
  .chart{margin-top:14px;display:flex;flex-direction:column;min-height:0;flex:1 1 auto}
  .chart svg{display:block;width:100%;flex:1 1 0;height:0;min-height:100px}
  .legend{display:flex;align-items:center;gap:16px;flex-wrap:wrap;
          font-size:var(--fs-1);color:var(--dim2);font-family:var(--mono);
          margin-top:8px;flex:0 0 auto;letter-spacing:.02em}
  .legend i{display:inline-block;width:7px;height:7px;border-radius:2px;margin-right:5px}
  .empty{color:var(--dim);font-size:var(--fs-2);line-height:1.7;padding:8px 0}

  /* ---------- 总览：6 等分记分板（不是卡片） ---------- */
  #card-ov{background:none;border:0;box-shadow:none;padding:2px 0 0;border-radius:0;overflow:visible}
  #card-ov .chead{display:none}
  .kpis{display:grid;grid-template-columns:repeat(6,minmax(0,1fr))}
  .kpi{position:relative;min-width:0;padding:0 24px}
  .kpi:first-child{padding-left:0}
  .kpi + .kpi{border-left:1px solid var(--line)}
  .kpi.grp{border-left-color:var(--line2)}
  .kpi.warn .v{color:var(--warn)}
  .kpi.bad .v{color:var(--bad)}
  .kpi .k{font-size:var(--fs-1);color:var(--dim2);letter-spacing:.06em;
          white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .kpi .v{font-family:var(--mono);font-size:var(--fs-5);font-weight:600;line-height:1;
          margin-top:7px;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
  .kpi .v small{font-size:var(--fs-2);color:var(--dim2);font-weight:400;margin-left:5px;letter-spacing:0}
  .kpi .sub{font-size:var(--fs-1);color:var(--dim2);font-family:var(--mono);
            margin-top:7px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}

  /* ---------- 主机：三栏 + 竖发丝线 ---------- */
  .hostgrid{display:grid;grid-template-columns:236px minmax(0,1fr) minmax(0,1.02fr);
            gap:0;height:100%;align-items:start}
  .hostgrid > .hcol{min-width:0;display:flex;flex-direction:column;padding:0 22px}
  .hostgrid > .hcol:first-child{padding-left:0}
  .hostgrid > .hcol:last-child{padding-right:0}
  .hostgrid > .hcol + .hcol{border-left:1px solid var(--line)}
  .hcol-a{gap:10px}
  .cpunum{display:flex;align-items:baseline;gap:8px}
  .cpunum b{font-family:var(--mono);font-size:var(--fs-6);font-weight:600;line-height:1;
            letter-spacing:-.04em;font-variant-numeric:tabular-nums}
  .cpunum span{font-size:var(--fs-1);color:var(--dim2);letter-spacing:.1em}
  .hostbars{display:flex;flex-direction:column;gap:16px}
  /* CPU 那个数值已在上面用 38px 写过一遍，条上再写一遍就是重复 => 只留条 */
  .hcol-a .hostbars .bar:first-child .lab{display:none}
  .hcol-b .tiles{margin-top:0}
  .hcol-c{gap:12px;height:100%}

  /* ---------- 存储表：一个表头 + 两行数据，标签不重复 ---------- */
  .diskstrip{flex:0 0 auto}
  .dhead,.drow{display:grid;grid-template-columns:minmax(0,1fr) 74px 74px 58px 58px 52px;
               gap:10px;align-items:center}
  .dhead{font-size:10px;color:var(--dim2);letter-spacing:.1em;
         padding-bottom:6px;border-bottom:1px solid var(--line)}
  .dhead > div:not(:first-child){text-align:right}
  .drow{padding:9px 0}
  .drow + .drow{border-top:1px solid var(--line-soft)}
  .dname{font-size:12.5px;font-weight:600;letter-spacing:-.01em;
         white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .dmeta{font-size:10.5px;color:var(--dim2);font-family:var(--mono);margin-top:2px;
         white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .dio{font-family:var(--mono);font-size:14px;font-weight:600;text-align:right;
       letter-spacing:-.02em;font-variant-numeric:tabular-nums;white-space:nowrap}
  .dio small{font-size:10px;color:var(--dim2);font-weight:400;margin-left:2px}
  .dio.warn{color:var(--warn)}
  .dio.bad{color:var(--bad)}
  .dstat{text-align:right;font-size:var(--fs-1);font-weight:600;letter-spacing:.04em}
  .dstat.ok{color:var(--good)}
  .dstat.bad{color:var(--bad)}
  .dstat.na{color:var(--dim2);font-weight:400}

  /* ---------- 页脚 ---------- */
  footer{
    margin-top:10px;padding-top:10px;color:var(--dim2);font-size:var(--fs-1);font-family:var(--mono);
    display:flex;gap:16px;flex-wrap:wrap;border-top:1px solid var(--line);
  }

  /* ---------- 响应式（只在真放不下时才变，不做「凭感觉的断点」） ---------- */
  @media (min-width:1900px){
    .kpi{padding:0 28px}
  }
  @media (max-width:1520px){
    .kpis{grid-template-columns:repeat(3,minmax(0,1fr));row-gap:16px}
    .kpi{padding:0 20px}
    .kpi:nth-child(4){border-left:0;padding-left:0}
    .hostgrid{grid-template-columns:200px minmax(0,1fr) minmax(0,1fr)}
    .hostgrid > .hcol{padding:0 16px}
  }
  @media (max-width:1160px){
    main{grid-template-columns:1fr;grid-template-rows:auto auto auto auto}
    .hostgrid{grid-template-columns:minmax(0,1fr)}
    .hostgrid > .hcol{padding:0;border-left:0}
    .hostgrid > .hcol + .hcol{margin-top:16px;padding-top:16px;border-top:1px solid var(--line)}
    .hcol-c{height:auto}
    .chart svg{min-height:120px}
  }
  @media (max-width:560px){
    body{padding:10px 12px 10px}
    .top{grid-template-columns:104px minmax(0,1fr);gap:14px}
    .ring{width:104px;height:104px}
    .ring .val b{font-size:26px}
    .tiles{grid-template-columns:repeat(2,minmax(0,1fr))}
    .dhead,.drow{grid-template-columns:minmax(0,1fr) 64px 64px 50px 50px 44px}
  }

"""

new = HEAD + CSS + TAIL
if crlf:
    new = new.replace("\n", "\r\n")
io.open(P, "wb").write(new.encode("utf-8"))
print("bytes", len(new.encode("utf-8")), "md5", hashlib.md5(new.encode("utf-8")).hexdigest())
print("crlf", crlf, "| style count", new.count("<style>"))
