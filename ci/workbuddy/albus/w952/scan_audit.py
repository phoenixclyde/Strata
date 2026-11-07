# -*- coding: utf-8 -*-
"""AUDIT24 mechanical layer: scan W900-W951 for closure claims, evidence level, banners."""
import glob, os, re, json, io

DEPLOY = "D:/workbuddy_space/strata_ws/deploy"

VERDICT = re.compile(r"(DONE_NEG|判否|不做|已结|不采纳|撤回|证否|判负|放弃)")
CLAIM_DONE = re.compile(r"(判否|不做|已结|不采纳|证否)")
EVID_A = re.compile(r"(A 级|A级|实测|跑过|docker logs|run id|停服 A/B|CV [0-9])")
EVID_C = re.compile(r"(C 级|C级|推算|估算|Amdahl|理论上限|外推)")
BANNER = re.compile(r"(作废|已被.*取代|撤回|superseded|口径已改|本条已废)")

def docs():
    out = []
    for p in sorted(glob.glob(os.path.join(DEPLOY, "W*.md"))):
        m = re.match(r"W(\d+)", os.path.basename(p))
        if not m:
            continue
        n = int(m.group(1))
        if n >= 900:
            out.append((n, p))
    return out

def main():
    rows = []
    for n, p in docs():
        s = io.open(p, encoding="utf-8", errors="replace").read()
        lines = s.split("\n")
        head = lines[0][:90] if lines else ""
        has_banner = bool(BANNER.search("\n".join(lines[:14])))
        # R claims: lines that mention Rxx together with verdict words
        claims = {}
        for i, ln in enumerate(lines, 1):
            ids = re.findall(r"\bR(\d{1,2})\b", ln)
            if not ids:
                continue
            if CLAIM_DONE.search(ln):
                for rid in ids:
                    claims.setdefault("R" + rid, []).append((i, ln.strip()[:120]))
        a = len(EVID_A.findall(s)); c = len(EVID_C.findall(s))
        rows.append(dict(w="W%d" % n, file=os.path.basename(p), bytes=len(s),
                         banner=has_banner, A=a, C=c, claims=claims, head=head))
    json.dump(rows, io.open("D:/workbuddy_space/strata_ws/albus/w952/scan.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    # compact print
    for r in rows:
        cl = ",".join(sorted(r["claims"].keys()))
        print("%-6s %-6d banner=%-5s A=%-3d C=%-3d claims[%s]  %s" %
              (r["w"], r["bytes"], r["banner"], r["A"], r["C"], cl, r["head"][:60]))

if __name__ == "__main__":
    main()
