#!/usr/bin/env python3
"""ci/osv_scan.py — is any pinned crate inside a known advisory range?  (Python 3.8+, standard library only)

Why this exists (W1183/W1184)
-----------------------------
GitHub's Dependabot only knows GitHub's Advisory Database.  On 2026-11-22 the desktop lock carried four
in-range advisories that Dependabot could not have reported: GHSA-hrj5-67jp-wqp9 (url) and
GHSA-jh2m-fhpj-3vr7 (rustix) return 404 from /advisories and 0 hits from /advisories?ghsa_id=, and
RUSTSEC-2026-0382/0383 (rustls-webpki, webpki-root-certs) have no GHSA at all.  So Dependabot's own
diagnostic "security_update_not_possible" must never be read as "no fix exists": it means "no fix that
this database can express".  That misreading is why `zip` sat at 4.6.1 for 25 days after
tauri-plugin-updater 2.14.1 (2026-10-28) had already shipped zip 9.

OSV aggregates RustSec + GHSA + CVE, so it sees both sides.  This script asks it per (crate, version).

Exit codes
----------
  0  clean, or every finding is on the allowlist and unexpired
  1  at least one unallowed finding, or an allowlist row has expired (expiry = "come back and look")
  3  OSV could not be reached after retries  -> the caller prints SKIPPED, never "pass"

The allowlist is a deliberate, dated exception: `package <TAB> vuln-id <TAB> YYYY-MM-DD <TAB> reason`.
A row matches a finding when the package matches and the row's id is the finding's id or one of its
aliases (OSV lists GHSA and RUSTSEC ids as aliases of the same issue).  Expired rows fail the scan.

    python3 ci/osv_scan.py --lock app/desktop/src-tauri/Cargo.lock --allow ci/OSV_ALLOW.tsv
    python3 ci/osv_scan.py --lock ... --allow ... --json /tmp/osv.json
"""
import argparse
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.request

API = os.environ.get("OSV_API", "https://api.osv.dev/v1")   # OSV_API is for rehearsing the unreachable path
UA = "strata-osv-scan/1.0 (+https://github.com/phoenixclyde/Strata)"
BATCH = 500
RETRIES = 3


def parse_lock(path):
    """Return [(name, version, source)] for every [[package]] that came from crates.io."""
    out = []
    name = ver = src = None
    in_pkg = False
    with open(path, encoding="utf-8-sig") as fh:
        for raw in fh:
            line = raw.strip()
            if line == "[[package]]":
                if in_pkg and name and ver and src and "crates.io" in src:
                    out.append((name, ver, src))
                name = ver = src = None
                in_pkg = True
            elif not in_pkg:
                continue          # the lockfile's own `version = 3` header is not a package
            elif line.startswith("name = "):
                name = line.split('"')[1]
            elif line.startswith("version = "):
                ver = line.split('"')[1]
            elif line.startswith("source = "):
                src = line.split('"')[1]
    if in_pkg and name and ver and src and "crates.io" in src:
        out.append((name, ver, src))
    return out


def _post(url, payload):
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _retry(fn, *args):
    last = None
    for attempt in range(RETRIES):
        try:
            return fn(*args)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            last = exc
            if attempt + 1 < RETRIES:
                time.sleep(3 * (attempt + 1))
    raise last


def query(pkgs):
    """[(name, version)] -> {(name, version): [vuln_id, ...]}.  Raises on network failure."""
    found = {}
    for i in range(0, len(pkgs), BATCH):
        chunk = pkgs[i:i + BATCH]
        payload = {"queries": [{"package": {"ecosystem": "crates.io", "name": n}, "version": v} for n, v in chunk]}
        result = _retry(_post, API + "/querybatch", payload)
        for pair, res in zip(chunk, result.get("results", [])):
            ids = [v["id"] for v in (res.get("vulns") or [])]
            if ids:
                found[pair] = ids
    return found


def describe(vuln_id, package):
    """Fetch one advisory: aliases, summary, fixed versions and the RustSec `informational` class."""
    doc = _retry(_get, API + "/vulns/" + vuln_id)
    fixed, informational = [], None
    for affected in doc.get("affected", []):
        if affected.get("package", {}).get("name") != package:
            continue
        informational = (affected.get("database_specific") or {}).get("informational") or informational
        for rng in affected.get("ranges", []):
            for event in rng.get("events", []):
                if "fixed" in event:
                    fixed.append(event["fixed"])
    return {
        "id": vuln_id,
        "aliases": doc.get("aliases") or [],
        "summary": (doc.get("summary") or "").strip(),
        "fixed": sorted(set(fixed)),
        "informational": informational,
    }


def load_allow(path):
    rows = []
    if not path or not os.path.exists(path):
        return rows
    with open(path, encoding="utf-8-sig") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 4:
                raise SystemExit("ALLOW_FORMAT: %r (want package<TAB>id<TAB>YYYY-MM-DD<TAB>reason)" % line)
            pkg, vid, expires, reason = parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip()
            try:
                exp = datetime.date.fromisoformat(expires)
            except ValueError:
                raise SystemExit("ALLOW_BAD_DATE: %r" % line)
            rows.append({"package": pkg, "id": vid, "expires": exp, "reason": reason})
    return rows


def main():
    ap = argparse.ArgumentParser(description="Scan a Cargo.lock against OSV (crates.io).")
    ap.add_argument("--lock", required=True)
    ap.add_argument("--allow", default="ci/OSV_ALLOW.tsv")
    ap.add_argument("--json", dest="json_out", default=None)
    args = ap.parse_args()

    pkgs = parse_lock(args.lock)
    if not pkgs:
        print("SUMMARY lock=%s packages=0 (no crates.io packages: nothing to ask)" % args.lock)
        return 0
    pairs = sorted({(n, v) for n, v, _s in pkgs})
    allow = load_allow(args.allow)

    try:
        hits = query(pairs)
    except Exception as exc:  # network, DNS, proxy, 5xx
        print("SKIPPED osv unreachable after %d tries: %s" % (RETRIES, exc))
        return 3

    today = datetime.date.today()
    findings, allowed, notes = [], [], []
    seen = {}
    for (name, ver), ids in sorted(hits.items()):
        for vid in ids:
            info = describe(vid, name)
            if info["informational"] == "unmaintained":
                # RustSec maintenance warnings carry no severity and no fixed version: record them, do not
                # fail the gate.  (glib is `unsound`, not `unmaintained`, so it still has to face the allowlist.)
                notes.append({"package": name, "version": ver, "id": vid, "summary": info["summary"]})
                continue
            key = (name, ver, tuple(sorted({vid} | set(info["aliases"]))))
            if key in seen:
                seen[key]["ids"].append(vid)
                continue
            row = None
            for cand in allow:
                if cand["package"] != name:
                    continue
                if cand["id"] == vid or cand["id"] in info["aliases"]:
                    row = cand
                    break
            entry = {"package": name, "version": ver, "ids": [vid], "aliases": info["aliases"],
                     "summary": info["summary"], "fixed": info["fixed"]}
            seen[key] = entry
            if row and row["expires"] >= today:
                entry.update({"expires": row["expires"].isoformat(), "reason": row["reason"],
                              "days_left": (row["expires"] - today).days})
                allowed.append(entry)
            else:
                entry["why"] = "allowlist expired on %s" % row["expires"].isoformat() if row else "not on the allowlist"
                findings.append(entry)

    for f in findings:
        print("FINDING %s %s %s fixed=%s — %s [%s]" % (
            f["package"], f["version"], ",".join(f["ids"]), ",".join(f["fixed"]) or "?",
            f["summary"][:100], f["why"]))
    for a in allowed:
        print("ALLOWED %s %s %s fixed=%s expires %s (%d days) — %s" % (
            a["package"], a["version"], ",".join(a["ids"]), ",".join(a["fixed"]) or "?",
            a["expires"], a["days_left"], a["reason"][:90]))
    for n in notes:
        print("INFO %s %s %s — %s" % (n["package"], n["version"], n["id"], n["summary"][:90]))
    print("SUMMARY lock=%s packages=%d findings=%d allowed=%d informational=%d" % (
        args.lock, len(pairs), len(findings), len(allowed), len(notes)))

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump({"lock": args.lock, "packages": len(pairs), "findings": findings, "allowed": allowed}, fh, indent=1)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
