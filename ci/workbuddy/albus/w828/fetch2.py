"""Fetch any of the 148 changed files that are still missing.
Uses Accept: application/vnd.github.raw for big files (the JSON contents API returns
content="" above 1 MB, and raw.githubusercontent.com 502s from this host)."""
import json
import os
import time
import urllib.error
import urllib.request

TOK = open('D:/workbuddy_space/strata_ws/deploy/tmp/_tok.txt').read().strip()
BASE = 'D:/workbuddy_space/strata_ws/albus/w828/'
DST = BASE + 'up028/'
REF = 'v0.2.8'
H = {'Authorization': 'Bearer ' + TOK, 'User-Agent': 'albus', 'Accept': 'application/vnd.github+json'}


def get(url, hdr=None, tries=5):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=hdr or H)
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except Exception as e:
            last = e
            time.sleep(1.0 + i)
    raise last


def main():
    files = json.load(open(BASE + 'compare_0271_028.json', encoding='utf-8'))
    names = [f['filename'] for f in files if f['status'] != 'removed']
    missing = [n for n in names if not os.path.exists(DST + n)]
    print('total %d, present %d, missing %d' % (len(names), len(names) - len(missing), len(missing)))
    if not missing:
        return
    t0 = time.time()
    for i, p in enumerate(missing):
        url = 'https://api.github.com/repos/Niko1221/Strata/contents/%s?ref=%s' % (urllib.parse.quote(p), REF)
        hdr = dict(H)
        hdr['Accept'] = 'application/vnd.github.raw'
        try:
            raw = get(url, hdr)
        except Exception as e:
            print('FAIL %s %s' % (p, e))
            continue
        out = DST + p
        os.makedirs(os.path.dirname(out) or DST, exist_ok=True)
        with open(out, 'wb') as fh:
            fh.write(raw)
        print('  %-56s %8d B  (%.0fs)' % (p, len(raw), time.time() - t0))
    print('done, still missing:', [n for n in names if not os.path.exists(DST + n)])


import urllib.parse  # noqa: E402

main()
