import io

P = "deploy/PROGRESS.tsv"
lines = io.open(P, encoding="utf-8").read().split("\n")
out = []
fixed = 0
for ln in lines:
    f = ln.split("\t")
    if len(f) == 11 and f[0].startswith(("B", "C")) and f[10].startswith("KW:"):
        body = f[10]
        sp = body.find(" ", 3)
        if sp > 0:
            tail = body[sp:].strip()
            f[10] = body[:sp]
            if tail and tail not in f[8]:
                f[8] = f[8].rstrip() + " " + tail
            ln = "\t".join(f)
            fixed += 1
            print("repaired", f[1], "| kw =", f[10])
    out.append(ln)
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(out))
print("rows repaired:", fixed)
