# -*- coding: utf-8 -*-
"""PR 前必查：main 是否已越过 v0.1.40.2 修掉 H5/H6（否则 base 选错 / 会重复提交）"""
import sys, time, base64, json
sys.path.insert(0, r"D:/workbuddy/_z_rk81")
sys.stdout.reconfigure(encoding='utf-8')
import _gh

UP = "Niko1221/Strata"
T0 = time.time()


def get(url, **kw):
    st, b, h = _gh.api(url, **kw)
    return st, _gh.jload(b), b


print('=== [1] main HEAD vs tag v0.1.40.2 ===')
st, d, b = get("https://api.github.com/repos/%s/commits/main" % UP)
main_sha = (d or {}).get('sha', '')
print('  main      = %s  %s' % (main_sha[:12], ((d or {}).get('commit') or {}).get('committer', {}).get('date')))
st, d, b = get("https://api.github.com/repos/%s/commits/v0.1.40.2" % UP)
tag_sha = (d or {}).get('sha', '')
print('  v0.1.40.2 = %s  %s' % (tag_sha[:12], ((d or {}).get('commit') or {}).get('committer', {}).get('date')))
if main_sha and tag_sha:
    st, d, b = get("https://api.github.com/repos/%s/compare/%s...%s" % (UP, tag_sha, main_sha))
    d = d or {}
    print('  compare: status=%s ahead_by=%s behind_by=%s  total_commits=%s' %
          (d.get('status'), d.get('ahead_by'), d.get('behind_by'), d.get('total_commits')))
    for c in (d.get('commits') or [])[:12]:
        print('    %s  %s' % (c.get('sha', '')[:10], (c.get('commit') or {}).get('message', '').split('\n')[0][:88]))
    print('  files changed by those commits:')
    for f in (d.get('files') or []):
        print('    %-72s %s' % (f.get('filename'), f.get('status')))
print()

print('=== [2] main 的两个目标文件是否已含修复 ===')
for path, needle in [
    ('include/strata/platform/hip_compat/strata_hip.h', '#define cudaEventBlockingSync'),
    ('CMakeLists.txt', 'STRATA_Q6K_EXPERTS OR STRATA_HIP_GFX906'),
    ('CMakeLists.txt', 'list(APPEND _strata_mmq_cuda_types q6_k)'),
]:
    st, d, b = get("https://api.github.com/repos/%s/contents/%s?ref=main" % (UP, path))
    if st == 200 and isinstance(d, dict) and d.get('content'):
        txt = base64.b64decode(d['content']).decode('utf-8', 'replace')
        n = txt.count(needle)
        print('  main:%-64s  %-58s x%d' % (path, needle[:56], n))
    else:
        print('  main:%-64s  HTTP %s' % (path, st))
print()

print('=== [3] tag v0.1.40.2 的同样两处（应有/应无）===')
for path, needle in [
    ('include/strata/platform/hip_compat/strata_hip.h', '#define cudaEventBlockingSync'),
    ('CMakeLists.txt', 'STRATA_Q6K_EXPERTS OR STRATA_HIP_GFX906'),
]:
    st, d, b = get("https://api.github.com/repos/%s/contents/%s?ref=v0.1.40.2" % (UP, path))
    if st == 200 and isinstance(d, dict) and d.get('content'):
        txt = base64.b64decode(d['content']).decode('utf-8', 'replace')
        print('  tag:%-65s  %-58s x%d' % (path, needle[:56], txt.count(needle)))
    else:
        print('  tag:%-65s  HTTP %s' % (path, st))
print()

print('=== [4] 与 gfx906 构建相关的 open PR（排除已列过的大批）===')
st, d, b = get("https://api.github.com/search/issues?q=repo:%s+is:pr+is:open+gfx906+build&per_page=20" % UP)
d = d or {}
print('  total=%s' % d.get('total_count'))
for it in (d.get('items') or []):
    print('    #%-6s %-72s %s' % (it.get('number'), (it.get('title') or '')[:70], it.get('created_at')))
print()
print('DONE %.1fs' % (time.time() - T0))
