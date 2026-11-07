import json, os, urllib.request, urllib.error

TOK = open('D:/workbuddy_space/strata_ws/deploy/tmp/_tok.txt').read().strip()
H = {'Authorization': 'Bearer ' + TOK, 'User-Agent': 'albus',
     'Accept': 'application/vnd.github+json'}


def api(url):
    r = urllib.request.Request(url, headers=H)
    try:
        return json.load(urllib.request.urlopen(r, timeout=90))
    except urllib.error.HTTPError as e:
        return {'_err': e.code, '_msg': e.read()[:200].decode('utf-8', 'replace')}
    except Exception as e:
        return {'_err': 'x', '_msg': str(e)[:150]}


REPO = 'KIntegrated/vllm-gfx906-mobydick'
LOCAL = '6ccbb03119'
HEAD = '3857591d'

print('=' * 100)
print('KI: all commits touching gfx906, last 60 (newest first)')
print('=' * 100)
c = api('https://api.github.com/repos/%s/commits?sha=main&per_page=60' % REPO)
n = 0
for x in c:
    m = x['commit']['message'].split('\n')[0]
    if 'gfx906' in m.lower() or 'int8' in m.lower() or 'dflash' in m.lower() or 'expert' in m.lower() or 'gemv' in m.lower():
        print('%s %s  %s' % (x['sha'][:8], x['commit']['author']['date'][:10], m[:92]))
        n += 1
print('  matched %d of %d' % (n, len(c)))

print()
print('=' * 100)
print('KI: compare local %s ... upstream %s  (what we are missing)' % (LOCAL, HEAD))
print('=' * 100)
d = api('https://api.github.com/repos/%s/compare/%s...%s' % (REPO, LOCAL, HEAD))
if '_err' in d:
    print('ERR', d)
else:
    print('status=%s  ahead_by=%s  total_commits=%s  files=%d' % (
        d.get('status'), d.get('ahead_by'), d.get('total_commits'), len(d.get('files') or [])))
    print()
    print('--- files changed, grouped ---')
    files = d.get('files') or []
    hot = [f for f in files if 'gfx906' in f['filename'].lower()
           or 'gemv' in f['filename'].lower() or 'moe' in f['filename'].lower()]
    print('gfx906/gemv/moe-related: %d of %d' % (len(hot), len(files)))
    for f in hot[:60]:
        print('   %-8s +%-6d -%-6d  %s' % (f['status'][:8], f['additions'], f['deletions'], f['filename']))
