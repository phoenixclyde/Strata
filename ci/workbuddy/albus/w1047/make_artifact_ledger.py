"""Build ci/provenance/artifact_ledger.tsv from live /data/bin + REBUILD_RECIPE.tsv."""
import io
import pathlib
import re

ROOT = pathlib.Path(r"D:/workbuddy_space/strata_ws")
OUT = ROOT / "albus/w1047/bundle/stage/ci/provenance/artifact_ledger.tsv"
OUT.parent.mkdir(parents=True, exist_ok=True)
INV = ROOT / "albus/w1047/bin_inventory.txt"
RECIPE = ROOT / "deploy/REBUILD_RECIPE.tsv"

live = {}
for line in INV.read_text(encoding="utf-8", errors="replace").splitlines():
    f = line.split("\t")
    if len(f) >= 3 and f[0].startswith("strata-"):
        live[f[0]] = (f[1], f[2])

recipe = {}
for line in RECIPE.read_text(encoding="utf-8-sig", errors="replace").splitlines():
    if not line or line.startswith("#") or line.startswith("name\t"):
        continue
    f = line.split("\t")
    if len(f) >= 8:
        recipe[f[0]] = {
            "md5": f[1], "size": f[2], "source": f[3], "llama": f[4],
            "mmq": f[5], "build": f[6], "note": f[7],
        }

manual = {
    "strata-0.1.57-kvg": "W1040 manual stop/start install; deploy.sh gh_gate/evidence gate run locally, not by ci/deploy.sh",
    "strata-0.1.57-attn": "W1044 two windows + cold start; deploy.sh bypassed; D1-D6 run manually after install correction",
}
all_names = sorted(set(live) | set(recipe))
with OUT.open("w", encoding="utf-8", newline="\n") as f:
    f.write("artifact\tlive_size\tlive_md5\trecipe_source\trecipe_md5\tci_or_manual\tprovenance_note\n")
    for name in all_names:
        size, md5 = live.get(name, ("", ""))
        r = recipe.get(name, {})
        note = r.get("note", "")
        if name in manual:
            mode = "MANUAL"
            note = manual[name] + (" | " + note if note else "")
        elif r:
            mode = "RECIPE" if md5 and md5 == r.get("md5") else "RECIPE_MISMATCH"
        else:
            mode = "UNTRACKED"
        f.write("\t".join([name, size, md5, r.get("source", ""), r.get("md5", ""), mode, note.replace("\t", " ")]) + "\n")
print("artifact rows", len(all_names))
print(OUT)
