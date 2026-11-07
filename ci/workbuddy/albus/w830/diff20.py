# -*- coding: utf-8 -*-
"""Diff our lost files (src0271 versions) against upstream v0.2.7.1 to see what the local change was."""
import difflib, io, json, os, tarfile, urllib.request

BASE = 'D:/workbuddy_space/strata_ws/albus/w830'
TOK = open('D:/workbuddy_space/strata_ws/deploy/tmp/_tok.txt').read().strip()
H = {'Authorization': 'Bearer ' + TOK, 'User-Agent': 'albus', 'Accept': 'application/vnd.github.raw'}

os.makedirs(BASE + '/lost20', exist_ok=True)
with tarfile.open(BASE + '/lost20.tgz') as t:
    t.extractall(BASE + '/lost20')

names = [l.strip() for l in io.open(BASE + '/lost20.txt', encoding='utf-8') if l.strip()] \
    if os.path.exists(BASE + '/lost20.txt') else None
if names is None:
    names = []
    for dp, dn, fn in os.walk(BASE + '/lost20'):
        for f in fn:
            p = os.path.join(dp, f)
            names.append(os.path.relpath(p, BASE + '/lost20').replace('\\', '/'))
    names.sort()

def up(path):
    url = 'https://api.github.com/repos/Niko1221/Strata/contents/%s?ref=v0.2.7.1' % path
    r = urllib.request.Request(url, headers=H)
    with urllib.request.urlopen(r, timeout=120) as resp:
        return resp.read().decode('utf-8', 'replace')

summary = []
for n in names:
    lp = os.path.join(BASE, 'lost20', n)
    if not os.path.exists(lp):
        continue
    ours = io.open(lp, encoding='utf-8', errors='replace').read()
    try:
        theirs = up(n)
    except Exception as e:
        print('%-46s FETCH FAIL %s' % (n, e)); continue
    d = list(difflib.unified_diff(theirs.split('\n'), ours.split('\n'), 'upstream0271', 'ours0271', lineterm='', n=1))
    adds = sum(1 for x in d if x.startswith('+') and not x.startswith('+++'))
    dels = sum(1 for x in d if x.startswith('-') and not x.startswith('---'))
    summary.append((n, adds, dels, d))
    print('=' * 100)
    print('%-46s  +%d -%d' % (n, adds, dels))
    for line in d[:26]:
        print('   ', line[:170])

print()
print('%-46s %5s %5s' % ('file', '+', '-'))
for n, a, b, _ in sorted(summary, key=lambda x: -(x[1] + x[2])):
    print('%-46s %5d %5d' % (n, a, b))
