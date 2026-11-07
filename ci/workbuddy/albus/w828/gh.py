import json, os, sys, urllib.request, urllib.error

TOK = open('D:/workbuddy_space/strata_ws/deploy/tmp/_tok.txt').read().strip()
OUT = 'D:/workbuddy_space/strata_ws/albus/w828/'
os.makedirs(OUT, exist_ok=True)


def api(path, raw=False):
    url = 'https://api.github.com' + path
    req = urllib.request.Request(url, headers={
        'Authorization': 'Bearer ' + TOK,
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'albus',
        'X-GitHub-Api-Version': '2022-11-28',
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read()
            rem = r.headers.get('X-RateLimit-Remaining')
            print('[%s] remaining=%s len=%d' % (path, rem, len(body)))
            return json.loads(body) if not raw else body
    except urllib.error.HTTPError as e:
        print('[ERR] %s %s %s' % (path, e.code, e.read()[:300]))
        return None


def main():
    rep = 'Niko1221/Strata'
    rel = api('/repos/%s/releases?per_page=4' % rep)
    if rel:
        with open(OUT + 'releases.json', 'w', encoding='utf-8') as f:
            json.dump(rel, f, ensure_ascii=False, indent=1)
        for r in rel:
            print('REL', r['tag_name'], r['published_at'], len(r.get('body') or ''))

    tags = api('/repos/%s/tags?per_page=10' % rep)
    if tags:
        print('TAGS', [t['name'] for t in tags])

    # recent commits touching src/ include/ CMakeLists
    for p in ['src', 'include']:
        c = api('/repos/%s/commits?path=%s&per_page=40' % (rep, p))
        if c:
            with open(OUT + 'commits_%s.json' % p, 'w', encoding='utf-8') as f:
                json.dump(c, f, ensure_ascii=False, indent=1)
            print('--- commits path=%s (%d) ---' % (p, len(c)))
            for x in c:
                print(x['sha'][:8], x['commit']['author']['date'], x['commit']['message'].split('\n')[0][:110])


main()
