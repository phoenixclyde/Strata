import io
p = "/home/albus/strata166/pr/strata-fork/.github/workflows/downstream-gate.yml"
s = io.open(p, encoding="utf-8").read()
bad = ("          persist-credentials: false\n"
       "            # W1029: a depth-1 checkout has no tags, and every tag-based check then fails for a\n"
       "            # reason that has nothing to do with the change.  Full history + tags.\n"
       "            fetch-depth: 0\n"
       "            fetch-tags: true\n")
good = ("          persist-credentials: false\n"
        "          # W1029: a depth-1 checkout has no tags, and every tag-based check then fails for a\n"
        "          # reason that has nothing to do with the change.  Full history + tags.\n"
        "          fetch-depth: 0\n"
        "          fetch-tags: true\n")
assert bad in s, "bad block not found"
io.open(p, "w", encoding="utf-8", newline="\n").write(s.replace(bad, good, 1))
print("indent fixed")
