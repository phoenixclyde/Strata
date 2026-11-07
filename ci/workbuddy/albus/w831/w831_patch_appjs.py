#!/usr/bin/env python3
"""W831: re-apply the only WEB-UI delta upstream never absorbed -- the PCIe peak suffix.

Upstream v0.2.8 already ships 74 of our 78 added lines (images tab, saveApiKey,
prefill rate, sampling defaults, sparkline top). The only line upstream lacks is
the `peak NN MB/s` suffix on the PCIe card, which pairs with TEL-PCIE.
"""
import io, sys, os, shutil

P = "/home/albus/strata166/src028/serve/web/app.js"

src = io.open(P, encoding="utf-8").read()

if "ALBUS-W831" in src:
    print("already patched")
    sys.exit(0)

anchor_gen = '  const gen = hw.gpu_pcie_gen_max || hw.gpu_pcie_gen;\n'
assert src.count(anchor_gen) == 1, "anchor gen: count=%d" % src.count(anchor_gen)

anchor_tail = ('            (hw.gpu_pcie_gen && gen && hw.gpu_pcie_gen < gen ? ` \u00b7 idle Gen${hw.gpu_pcie_gen}` : ""));\n')
assert src.count(anchor_tail) == 1, "anchor tail: count=%d" % src.count(anchor_tail)

new_gen = anchor_gen + (
    '  const pciePk = Math.max(0, ...(h.gpu_pcie_rx_mb || []).filter((x) => x != null));'
    ' /* ALBUS-W831 */\n'
)
new_tail = (
    '            (hw.gpu_pcie_gen && gen && hw.gpu_pcie_gen < gen ? ` \u00b7 idle Gen${hw.gpu_pcie_gen}` : "") +\n'
    '            (pciePk >= 1 ? ` \u00b7 peak ${fmt(pciePk, pciePk < 10 ? 1 : 0)} MB/s` : ""));'
    ' /* ALBUS-W831 */\n'
)

out = src.replace(anchor_gen, new_gen, 1).replace(anchor_tail, new_tail, 1)
assert out != src
assert out.count("ALBUS-W831") == 2, out.count("ALBUS-W831")

bak = P + ".bak-w831b"
if not os.path.exists(bak):
    shutil.copy2(P, bak)

io.open(P, "w", encoding="utf-8", newline="\n").write(out)

lines = out.split("\n")
for i, l in enumerate(lines):
    if "ALBUS-W831" in l:
        print("%d: %s" % (i + 1, l))
print("bytes", len(out.encode()), "was", len(src.encode()))
