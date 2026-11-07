import json, os, sys, time, urllib.request, urllib.error

TOK = None
for p in ['D:/workbuddy_space/strata_ws/deploy/tmp/_tok.txt',
          'D:/workbuddy_space/strata_ws/albus/w828/_tok.txt']:
    if os.path.exists(p):
        TOK = open(p).read().strip()
        break
if not TOK:
    print('NO TOKEN'); sys.exit(1)

H = {'Authorization': 'Bearer ' + TOK, 'User-Agent': 'albus',
     'Accept': 'application/vnd.github+json'}


def api(url):
    r = urllib.request.Request(url, headers=H)
    try:
        return json.load(urllib.request.urlopen(r, timeout=60))
    except urllib.error.HTTPError as e:
        return {'_err': e.code, '_msg': e.read()[:160].decode('utf-8', 'replace')}
    except Exception as e:
        return {'_err': 'x', '_msg': str(e)[:120]}


REPOS = [
    ('ggml-org/llama.cpp', 'llama.cpp 上游'),
    ('eslowney/llama.cpp-gfx906', 'llama.cpp-gfx906 (D=128 FA)'),
    ('fuutott/llama.cpp-gfx906', 'llama.cpp-gfx906 (DPP/Q8 ckpt)'),
    ('iacopPBK/llama.cpp-gfx906', 'llama.cpp-gfx906 (alt)'),
    ('skyne98/llama.cpp-gfx906', 'skyne98 fork?'),
    ('KIntegrated/vllm-gfx906-mobydick', 'KI 上游'),
    ('nick413-bit/gfx906-fa-vllm', 'gfx906-fa-vllm (nick)'),
    ('cassettesgoboom/gfx906-fa-vllm', 'gfx906-fa-vllm (orig)'),
    ('Niko1221/Strata', 'Strata 上游'),
]

print('=' * 96)
for full, label in REPOS:
    d = api('https://api.github.com/repos/' + full)
    if '_err' in d:
        print('%-34s %-34s  %s %s' % (full, label, d['_err'], d.get('_msg', '')[:60]))
        continue
    br = d.get('default_branch', '?')
    push = (d.get('pushed_at') or '')[:16].replace('T', ' ')
    sz = d.get('size', 0)
    print('%-34s %-32s branch=%-12s pushed=%s  size=%sKB' % (full, label, br, push, sz))

print()
print('=' * 96)
print('最近提交（每个仓库默认分支，各 5 条）')
print('=' * 96)
for full, label in REPOS:
    d = api('https://api.github.com/repos/' + full)
    if '_err' in d:
        continue
    br = d.get('default_branch', 'master')
    c = api('https://api.github.com/repos/%s/commits?sha=%s&per_page=5' % (full, br))
    if isinstance(c, dict):
        print('%-34s ERR %s' % (full, c.get('_msg')))
        continue
    print()
    print('## %s  (%s)' % (full, label))
    for x in c:
        msg = x['commit']['message'].split('\n')[0][:88]
        print('   %s  %s  %s' % (x['sha'][:8], x['commit']['author']['date'][:10], msg))
