# -*- coding: utf-8 -*-
"""本地静态校验：抽 script -> node --check -> CSS 状态机 -> 标签配平 -> 复用 _test.js（路径改写）"""
import io, os, re, subprocess, sys

W = r"D:/workbuddy_space/strata_ws/albus/netdata_v37"
P = os.path.join(W, "gpu.html")
html = io.open(P, encoding="utf-8").read()

# 1) 抽所有 <script> 块（页面有两个：自检块 + 主块）
blocks = re.findall(r"<script>(.*?)</script>", html, re.S)
print("SCRIPT_BLOCKS =", len(blocks), [len(b) for b in blocks])
js = "\n;\n".join("(function(){" + b + "\n})();" for b in blocks)
# 主块本身就是 IIFE，再包一层会改变 'use strict' 语义 => 这里只做语法检查，按原样拼接
js = "\n".join(blocks)
io.open(os.path.join(W, "_check.js"), "w", encoding="utf-8").write(js)

NODE = r"C:/Program Files/nodejs/node.exe"
if not os.path.isfile(NODE):
    NODE = "node"
r = subprocess.run([NODE, "--check", os.path.join(W, "_check.js")], capture_output=True)
print("NODE_CHECK rc=%d %s" % (r.returncode, r.stderr.decode("utf-8", "replace")[:600]))

# 2) CSS 状态机
css = html[html.index("<style>") + 7: html.index("</style>")]
i, state, warns = 0, "code", []
while i < len(css) - 1:
    two = css[i:i + 2]
    if state == "code":
        if two == "/*":
            state = "comment"; i += 2; continue
        if two == "*/":
            warns.append("孤立 */ @%d" % i); i += 2; continue
    else:
        if two == "*/":
            state = "code"; i += 2; continue
        if two == "/*":
            warns.append("注释内嵌套 /* @%d" % i); i += 2; continue
    i += 1
if state == "comment":
    warns.append("注释未闭合")
ob, cb = css.count("{"), css.count("}")
print("CSS {=%d }=%d  /*=%d */=%d  warns=%s" % (ob, cb, css.count("/*"), css.count("*/"), warns or "none"))
print("CSS_COMMENT_CMT =", css.count("/*="))  # 防止有人在注释里写 */ (同族坑)

# 3) 标签配平
for tag in ["section", "div", "svg", "header", "footer", "main", "span"]:
    o = len(re.findall(r"<%s[\s>]" % tag, html))
    c = len(re.findall(r"</%s>" % tag, html))
    print("%-8s open=%d close=%d %s" % (tag, o, c, "OK" if o == c else "<<< MISMATCH"))

# 4) 复用 _test.js：把固定路径改成工作目录
t = io.open(r"D:/workbuddy/netdata-dashboard/_test.js", encoding="utf-8").read()
t = t.replace("D:/workbuddy/netdata-dashboard/", W.replace("\\", "/") + "/")
io.open(os.path.join(W, "_test_v37.js"), "w", encoding="utf-8").write(t)
print("WROTE _test_v37.js")
