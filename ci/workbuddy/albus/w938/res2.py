#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W938: resolve rebase conflict 2 (705e09f7).
Upstream inserted the STRATA_MTP_ROOM_MIN block exactly where our commit adds
tr("previous commit joined").  Keep upstream's block verbatim and put the trace point
immediately before it (same place in the flow: right after the previous commit wait).
"""
import io, re, sys

p = "/home/albus/strata166/work/rebase-trial/src/program/generate.cpp"
s = io.open(p, encoding="utf-8").read()
pat = re.compile(r"<<<<<<< [^\n]*\n(.*?)=======\n(.*?)>>>>>>> [^\n]*\n", re.S)
blocks = pat.findall(s)
print("conflict blocks:", len(blocks))
if len(blocks) != 1:
    print("unexpected block count"); sys.exit(2)
ours, theirs = blocks[0]
print("ours lines:", ours.count("\n"), " theirs lines:", theirs.count("\n"))
print("theirs is our tr() line:", theirs.strip() == 'tr("previous commit joined");')

merged = '            tr("previous commit joined");\n' + ours
s = pat.sub(lambda m: merged, s, count=1)
io.open(p, "w", encoding="utf-8").write(s)
print("markers left:", s.count("<<<<<<<"))
print("both present:",
      'tr("previous commit joined")' in s,
      "STRATA_MTP_ROOM_MIN" in s or "mtp_room_open" in s)
