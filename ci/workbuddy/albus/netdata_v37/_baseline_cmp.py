# -*- coding: utf-8 -*-
"""基线对照：用同一份 _test.js 跑 v36（改造前）与 v37（改造后），比较 PROBLEMS 差异。
目的：把「测试文件本身过期」与「本次改动引入的回归」分开。
"""
import io, os, re, subprocess

W = r"D:/workbuddy_space/strata_ws/albus/netdata_v37"
V36 = os.path.join(W, "_v36")
os.makedirs(V36, exist_ok=True)
NODE = r"C:/Users/clyde/.workbuddy/binaries/node/versions/22.22.2-6/node"

def prep(html_path, outdir):
    html = io.open(html_path, encoding="utf-8").read()
    blocks = re.findall(r"<script>(.*?)</script>", html, re.S)
    io.open(os.path.join(outdir, "_check.js"), "w", encoding="utf-8").write("\n".join(blocks))
    io.open(os.path.join(outdir, "gpu.html"), "w", encoding="utf-8").write(html)

def mk_test(outdir):
    t = io.open(r"D:/workbuddy/netdata-dashboard/_test.js", encoding="utf-8").read()
    t = t.replace("D:/workbuddy/netdata-dashboard/", outdir.replace("\\", "/") + "/")
    # 桩缺 removeAttribute（v36 起页面在 IDLE 分支会调它）=> 补上，否则两个版本都在同一处崩
    t = t.replace("setAttribute(){}, getAttribute(){ return null; },",
                  "setAttribute(){}, getAttribute(){ return null; }, removeAttribute(){},")
    p = os.path.join(outdir, "_test.js")
    io.open(p, "w", encoding="utf-8").write(t)
    return p

def run(p, outtag):
    subprocess.run([NODE, p], capture_output=True, timeout=180)
    o = os.path.join(os.path.dirname(p), "_test_out.txt")
    s = io.open(o, encoding="utf-8", errors="replace").read()
    probs = s.split("PROBLEMS = ")[-1].split("\nverdict")[0]
    return probs.strip()

prep(os.path.join(W, "gpu.html.v36.bak"), V36)
p36 = mk_test(V36)
prep(os.path.join(W, "gpu.html"), W)
p37 = mk_test(W)

a = run(p36, "v36")
b = run(p37, "v37")
print("=== v36 PROBLEMS ===\n" + a)
print("\n=== v37 PROBLEMS ===\n" + b)
sa = set(x.strip() for x in a.split(";") if x.strip())
sb = set(x.strip() for x in b.split(";") if x.strip())
print("\n=== 仅在 v37 新增（= 本次改动引入）===")
for x in sorted(sb - sa):
    print("  + " + x)
print("=== 仅在 v36（= 被本次改动修掉/消失）===")
for x in sorted(sa - sb):
    print("  - " + x)
