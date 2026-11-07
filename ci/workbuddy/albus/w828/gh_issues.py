import json
import urllib.request

TOK = open('D:/workbuddy_space/strata_ws/deploy/tmp/_tok.txt').read().strip()
H = {'Authorization': 'Bearer ' + TOK, 'User-Agent': 'albus', 'Accept': 'application/vnd.github+json'}


def get(url):
    req = urllib.request.Request(url, headers=H)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


for n in (816, 1272, 4402):
    try:
        i = get('https://api.github.com/repos/Niko1221/Strata/issues/%d' % n)
        print('=== #%d  %s' % (n, i['title']))
        body = (i.get('body') or '')
        print(body[:1800].replace('\r', ''))
        print('--- comments:', i['comments'])
        if i['comments']:
            cs = get('https://api.github.com/repos/Niko1221/Strata/issues/%d/comments?per_page=10' % n)
            for c in cs[:3]:
                print('  *', (c.get('body') or '')[:700].replace('\r', ''))
        print()
    except Exception as e:
        print('#%d failed: %s' % (n, e))
