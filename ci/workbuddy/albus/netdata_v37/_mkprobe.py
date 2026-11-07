# -*- coding: utf-8 -*-
"""生成一个测量用副本：在原页面末尾追加一段只读探针，把布局尺寸写进 <title>。
用途：量出 v36（原尺寸）与 v37（现在超屏）的真实高度差，避免凭感觉改 CSS。
file:// 打开时页面自己会把 API 指向 http://192.168.50.166:19999（页面里已有这个分支）。
"""
import io, sys

src = sys.argv[1]
dst = sys.argv[2]

s = io.open(src, "rb").read().decode("utf-8")
assert "</body>" in s
probe = """
<script>
setTimeout(function(){
  function R(el){ if(!el) return null; var b=el.getBoundingClientRect(); return [Math.round(b.top),Math.round(b.height)]; }
  var cards = [].slice.call(document.querySelectorAll("main > .card")).map(function(c,i){
    var h = c.querySelector("h2");
    return (h?h.textContent:"card"+i) + ":" + R(c).join("/");
  });
  var out = {
    vw: innerWidth, vh: innerHeight,
    body: document.body.scrollHeight,
    doc: document.documentElement.scrollHeight,
    header: R(document.querySelector("header")),
    main: R(document.querySelector("main")),
    footer: R(document.querySelector("footer")),
    cards: cards
  };
  document.title = "METRICS " + JSON.stringify(out);
}, 6500);
</script>
</body>"""

s = s.replace("</body>", probe)
io.open(dst, "w", encoding="utf-8", newline="").write(s)
print("wrote", dst)
