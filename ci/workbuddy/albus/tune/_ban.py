import sys, io
BAN = ["\u21d2","\u2192","\u2264","\u2265","\u2713","\u2717","\u2705","\u274c","\u26a0","\u2b50","\u2605","\u2606","\u2218"]
p = sys.argv[1]
raw = open(p,"rb").read()
txt = raw.decode("utf-8")
cr = raw.count(b"\r")
lines = txt.split("\n")
hits = []
for i,l in enumerate(lines,1):
    for b in BAN:
        if b in l:
            hits.append((i,b,"U+%04X"%ord(b),l.strip()[:90]))
print("file:",p)
print("CR bytes:",cr)
print("BAN hits:",len(hits))
for h in hits[:40]: print("  L%d %s %s | %s"%h)
