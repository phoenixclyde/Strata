"""Fetch the 148 files that changed v0.2.7.1 -> v0.2.8 via the contents API
(raw.githubusercontent.com returned 502), verify no deletions, write a tree."""
import base64
import json
import os
import time
import urllib.error
import urllib.request

TOK = open('D:/workbuddy_space/strata_ws/deploy/tmp/_tok.txt').read().strip()
BASE = 'D:/workbuddy_space/strata_ws/albus/w828/'
DST = BASE + 'up028/'
H = {'Authorization': 'Bearer ' + TOK, 'User-Agent': 'albus', 'Accept': 'application/vnd.github+json'}
REF = 'v0.2.8'


def get(url, tries=4):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=H)
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read()
        except Exception as e:
            last = e
            time.sleep(1.5 * (i + 1))
    raise last


def main():
    files = json.load(open(BASE + 'compare_0271_028.json', encoding='utf-8'))
    os.makedirs(DST, exist_ok=True)
    todo = [f for f in files if f['status'] != 'removed']
    removed = [f['filename'] for f in files if f['status'] == 'removed']
    print('files=%d removed=%d' % (len(todo), len(removed)))
    t0 = time.time()
    n = 0
    big = []
    for f in todo:
        p = f['filename']
        url = 'https://api.github.com/repos/Niko1221/Strata/contents/%s?ref=%s' % (urllib.parse.quote(p), REF)
        js = json.loads(get(url))
        if isinstance(js, list):
            print('SKIP dir', p)
            continue
        raw = base64.b64decode(js['content']) if js.get('content') else get(js['download_url'])
        out = DST + p
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, 'wb') as fh:
            fh.write(raw)
        n += 1
        if len(raw) > 400000:
            big.append((p, len(raw)))
        if n % 20 == 0:
            print('  %d/%d  %.1fs' % (n, len(todo), time.time() - t0))
    print('done %d files in %.1fs' % (n, time.time() - t0))
    print('big:', big)
    with open(BASE + 'up028_manifest.json', 'w', encoding='utf-8') as fh:
        json.dump({'ref': REF, 'files': [f['filename'] for f in todo], 'removed': removed}, fh, indent=1)


import urllib.parse  # noqa: E402

main()
