# -*- coding: utf-8 -*-
"""Strata 上游侦察：最新 release / 我们是否已有 fork / #1083 现状 / 与 gfx906 相关的 open PR"""
import sys, time, json
sys.path.insert(0, r"D:/workbuddy/_z_rk81")
sys.stdout.reconfigure(encoding='utf-8')
import _gh

T0 = time.time()

def show(tag, st, body, limit=700):
    print('--- %s  [%.1fs] HTTP %s' % (tag, time.time() - T0, st))
    print(body[:limit].replace('\n', '\n    '))
    print()

UP = "Niko1221/Strata"
FK = "phoenixclyde/Strata"

st, b, h = _gh.api("https://api.github.com/user")
print('[auth] HTTP %s  login=%s  scopes=%s' % (st, (_gh.jload(b) or {}).get('login'), h.get('x-oauth-scopes')))
print()

# 1) 仓库概况
st, b, _ = _gh.api("https://api.github.com/repos/%s" % UP)
d = _gh.jload(b) or {}
print('=== [1] %s ===' % UP)
for k in ('full_name', 'default_branch', 'stargazers_count', 'forks_count',
          'pushed_at', 'updated_at', 'license', 'open_issues_count', 'size'):
    print('  %-20s : %s' % (k, d.get(k) if not isinstance(d.get(k), dict) else d.get(k, {}).get('spdx_id')))
print()

# 2) 最新 release / tag
st, b, _ = _gh.api("https://api.github.com/repos/%s/releases?per_page=5" % UP)
rels = _gh.jload(b) or []
print('=== [2] 最近 5 个 release ===')
for r in (rels if isinstance(rels, list) else []):
    print('  %-12s %s  target=%s' % (r.get('tag_name'), r.get('published_at'), (r.get('target_commitish') or '')[:12]))
print()

st, b, _ = _gh.api("https://api.github.com/repos/%s/tags?per_page=5" % UP)
tags = _gh.jload(b) or []
print('=== [2b] 最近 5 个 tag ===')
for t in (tags if isinstance(tags, list) else []):
    print('  %-14s %s' % (t.get('name'), (t.get('commit') or {}).get('sha', '')[:12]))
print()

# 3) 我们是否已有 fork
st, b, _ = _gh.api("https://api.github.com/repos/%s" % FK)
if st == 200:
    dd = _gh.jload(b) or {}
    print('=== [3] fork 已存在: %s  parent=%s  pushed_at=%s' %
          (dd.get('full_name'), (dd.get('parent') or {}).get('full_name'), dd.get('pushed_at')))
else:
    print('=== [3] fork 不存在（HTTP %s）=> 需要 POST /forks' % st)
print()

# 4) PR #1083 现状
st, b, _ = _gh.api("https://api.github.com/repos/%s/pulls/1083" % UP)
d = _gh.jload(b) or {}
if st == 200:
    print('=== [4] PR #1083 ===')
    print('  state=%s merged=%s merged_at=%s title=%s' %
          (d.get('state'), d.get('merged'), d.get('merged_at'), d.get('title')))
    print('  base=%s head=%s files=%s +%s/-%s' %
          ((d.get('base') or {}).get('ref'), (d.get('head') or {}).get('label'),
           d.get('changed_files'), d.get('additions'), d.get('deletions')))
else:
    print('=== [4] PR #1083 HTTP %s' % st)
print()

# 5) open PR 里与 gfx906 / hip 有关的
st, b, _ = _gh.api("https://api.github.com/repos/%s/pulls?state=open&per_page=100" % UP)
prs = _gh.jload(b) or []
print('=== [5] open PR 共 %d 条；其中标题/正文含 gfx906|hip|q6_k 的 ===' % (len(prs) if isinstance(prs, list) else -1))
for p in (prs if isinstance(prs, list) else []):
    t = ((p.get('title') or '') + ' ' + (p.get('body') or '')).lower()
    if any(k in t for k in ('gfx906', 'hip', 'q6_k', 'q6k', 'hipcc')):
        print('  #%-5s %-70s  by %s  %s' % (p.get('number'), (p.get('title') or '')[:68],
                                            (p.get('user') or {}).get('login'), p.get('created_at')))
print()

# 6) 搜索 q6_k / cudaEventBlockingSync
for q in ('q6_k', 'cudaEventBlockingSync', 'STRATA_HIP_GFX906'):
    st, b, _ = _gh.api("https://api.github.com/search/issues?q=repo:%s+%s&per_page=10"
                       % (UP, q.replace(' ', '+')))
    d = _gh.jload(b) or {}
    items = d.get('items') or []
    print('=== [6] search "%s": total=%s ===' % (q, d.get('total_count')))
    for it in items[:8]:
        kind = 'PR' if it.get('pull_request') else 'ISSUE'
        print('  %-5s #%-6s %-8s %-62s %s' % (kind, it.get('number'), it.get('state'),
                                              (it.get('title') or '')[:60], it.get('created_at')))
    print()

print('DONE  elapsed=%.1fs' % (time.time() - T0))
