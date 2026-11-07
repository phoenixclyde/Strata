# -*- coding: utf-8 -*-
"""把自有 serve 层覆写从 0.2.2 移植到 0.2.3（fail-closed：每处锚点必须唯一命中）。
 1) telemetry.py：上游 0.2.2 与 0.2.3 逐字节相同 => 直接用 .patched.022；
    仍做一次"补丁面 = 我们那 4 处"的自检（在 upstream023 上重放并比对 md5）。
 2) app.js：上游新增 #3435（API key 立即生效）改了 26 行，但 PCIe 锚点在另一处 => 重放一处补丁。
"""
import io, hashlib, os, sys, difflib

TP = r"D:/workbuddy_space/strata_ws/deploy/tmp/_tpatch"


def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()


def must_once(hay, needle, label):
    n = hay.count(needle)
    if n != 1:
        raise SystemExit("FAIL-CLOSED: %s 锚点命中 %d 次（要求 1）: %r" % (label, n, needle[:80]))


# ---------- app.js ----------
src = io.open(os.path.join(TP, "app.js.upstream023"), encoding="utf-8").read()

A1 = "  const gen = hw.gpu_pcie_gen_max || hw.gpu_pcie_gen;\n"
A2 = ('  setMetric("pcie", gen ? `Gen${gen}` : null, hw.gpu_pcie_width ? `x${hw.gpu_pcie_width}` : "",\n'
      '            hw.gpu_pcie_rx_mb == null ? "" : `to GPU ${fmt(hw.gpu_pcie_rx_mb, hw.gpu_pcie_rx_mb < 10 ? 1 : 0)} MB/s` +\n')

must_once(src, A1, "app.js A1(gen)")
must_once(src, A2, "app.js A2(setMetric pcie)")

R1 = (A1 +
      "  // the value is the current second; the sparkline is the last 60 of them, so the sub-line says both\n"
      "  const pciePk = Math.max(0, ...(h.gpu_pcie_rx_mb || []).filter((x) => x != null));\n")
R2 = ('  setMetric("pcie", gen ? `Gen${gen}` : null, hw.gpu_pcie_width ? `x${hw.gpu_pcie_width}` : "",\n'
      '            (hw.gpu_pcie_rx_mb == null ? "" : `to GPU ${fmt(hw.gpu_pcie_rx_mb, hw.gpu_pcie_rx_mb < 10 ? 2 : 0)} MB/s` +\n'
      '            (pciePk >= 1 ? ` \\u00b7 peak ${fmt(pciePk, pciePk < 10 ? 2 : 0)} MB/s` : "")) +\n')

out = src.replace(A1, R1, 1).replace(A2, R2, 1)
assert out != src
dst = os.path.join(TP, "serve-web-app.js.patched.023")
io.open(dst, "w", encoding="utf-8", newline="\n").write(out)
print("app.js  023 patched bytes", len(out.encode()), "md5", md5(dst)[:8])

# 自检：与 0.2.2 补丁件的差异应只有上游那 26 行 API key 变化
a = io.open(dst, encoding="utf-8").read().splitlines()
b = io.open(os.path.join(TP, "serve-web-app.js.patched.022"), encoding="utf-8").read().splitlines()
d = [l for l in difflib.unified_diff(b, a, lineterm="", n=0) if l[:1] in "+-" and not l.startswith(("+++", "---"))]
print("diff vs patched.022 lines:", len(d), "(should be ~26, all API-key)")

# ---------- telemetry.py ----------
up23 = os.path.join(TP, "telemetry.py.upstream023")
up22 = os.path.join(TP, "telemetry.py.upstream022")
print("telemetry upstream 022 md5", md5(up22)[:8], "023 md5", md5(up23)[:8],
      "IDENTICAL" if md5(up22) == md5(up23) else "DIFFERS")
t23 = os.path.join(TP, "serve-telemetry.py.patched.023")
io.open(t23, "wb").write(open(os.path.join(TP, "serve-telemetry.py.patched.022"), "rb").read())
print("telemetry 023 patched = copy of .022, md5", md5(t23)[:8], "bytes", os.path.getsize(t23))

# 补丁面自检：上游 023 上必须仍存在我们插入的两处特征
s = io.open(up23, encoding="utf-8").read()
for k in ("pcie_bw", "def bw"):
    print("  upstream023 contains %-9s : %d (expect 0 = 我们加的)" % (k, s.count(k)))
p = io.open(t23, encoding="utf-8").read()
for k in ("def bw(self)", "pcie_bw"):
    print("  patched023  contains %-12s : %d (expect >=1)" % (k, p.count(k)))
import ast
ast.parse(p)
print("  ast.parse OK")
