import json
import urllib.request

TOK = open('D:/workbuddy_space/strata_ws/deploy/tmp/_tok.txt').read().strip()
H = {'Authorization': 'Bearer ' + TOK, 'User-Agent': 'albus'}
url = 'https://api.github.com/repos/Niko1221/Strata/git/trees/v0.2.8?recursive=1'
req = urllib.request.Request(url, headers=H)
with urllib.request.urlopen(req, timeout=120) as r:
    t = json.loads(r.read())
print('truncated', t.get('truncated'), 'entries', len(t['tree']))
blobs = {e['path']: e['sha'] for e in t['tree'] if e['type'] == 'blob'}
print('blobs', len(blobs))
out = 'D:/workbuddy_space/strata_ws/albus/w828/tree_028.json'
json.dump(blobs, open(out, 'w'), indent=0)
print('wrote', out)
