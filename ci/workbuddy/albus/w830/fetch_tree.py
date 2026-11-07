# -*- coding: utf-8 -*-
"""Fetch the recursive blob map of a tag (default v0.2.7.1) and save it as json."""
import json, os, sys, urllib.request

TOK = open('D:/workbuddy_space/strata_ws/deploy/tmp/_tok.txt').read().strip()
TAG = sys.argv[1] if len(sys.argv) > 1 else 'v0.2.7.1'
OUT = sys.argv[2] if len(sys.argv) > 2 else 'D:/workbuddy_space/strata_ws/albus/w830/tree_0271.json'

h = {'Authorization': 'Bearer ' + TOK, 'User-Agent': 'albus'}


def get(url):
    r = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(r, timeout=120) as resp:
        return json.loads(resp.read())


ref = get('https://api.github.com/repos/Niko1221/Strata/git/ref/tags/' + TAG)
sha = ref['object']['sha']
if ref['object']['type'] == 'tag':
    tag = get('https://api.github.com/repos/Niko1221/Strata/git/tags/' + sha)
    sha = tag['object']['sha']
print('tag', TAG, '-> commit', sha)

tree = get('https://api.github.com/repos/Niko1221/Strata/git/trees/%s?recursive=1' % sha)
print('truncated', tree.get('truncated'))
files = {e['path']: e['sha'] for e in tree['tree'] if e['type'] == 'blob'}
json.dump(files, open(OUT, 'w'), ensure_ascii=False)
print('files', len(files), '->', OUT)
