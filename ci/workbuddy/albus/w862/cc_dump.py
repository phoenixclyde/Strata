#!/usr/bin/env python3
import json
B = "/home/albus/strata166/gfx029-build"
d = json.load(open(B + "/compile_commands.json"))
print("entries:", len(d))
hits = [e for e in d if "mmvq" in e["file"].lower()]
print("mmvq hits:", len(hits))
for e in hits[:3]:
    print("FILE:", e["file"])
    print("CMD :", e["command"][:1500])
    print("-" * 60)
print("sample files:", [e["file"].split("/")[-1] for e in d[:8]])
