import io, re
p = "/home/albus/strata166/pr/strata-fork/.github/workflows/downstream-gate.yml"
lines = io.open(p, encoding="utf-8").read().split("\n")
out = []
done = False
for i, l in enumerate(lines):
    out.append(l)
    if (not done) and l.strip() == "persist-credentials: false":
        ind = " " * (len(l) - len(l.lstrip()) + 2)
        out.append(ind + "# W1029: a depth-1 checkout has no tags, and every tag-based check then fails for a")
        out.append(ind + "# reason that has nothing to do with the change.  Full history + tags.")
        out.append(ind + "fetch-depth: 0")
        out.append(ind + "fetch-tags: true")
        done = True
assert done, "no persist-credentials line"
io.open(p, "w", encoding="utf-8", newline="\n").write("\n".join(out))
print("workflow patched")
