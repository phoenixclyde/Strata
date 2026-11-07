# -*- coding: utf-8 -*-
"""在 phoenixclyde 下建 Niko1221/Strata 的 fork，并等到可用。"""
import sys, time, json
sys.path.insert(0, r"D:/workbuddy/_z_rk81")
sys.stdout.reconfigure(encoding='utf-8')
import _gh

UP = "Niko1221/Strata"
FK = "phoenixclyde/Strata"

st, b, _ = _gh.api("https://api.github.com/repos/%s" % FK)
print('[pre] fork 现状 HTTP %s' % st)
if st == 200:
    d = _gh.jload(b) or {}
    print('  已存在: %s  default=%s  parent=%s  created=%s' %
          (d.get('full_name'), d.get('default_branch'), (d.get('parent') or {}).get('full_name'), d.get('created_at')))
else:
    print('[1] POST /repos/%s/forks' % UP)
    st, b, _ = _gh.api("https://api.github.com/repos/%s/forks" % UP, method="POST",
                       payload={"name": "Strata", "default_branch_only": False}, timeout=120)
    print('    HTTP %s' % st)
    d = _gh.jload(b) or {}
    if st in (200, 201, 202):
        print('    created -> %s  (owner=%s)' % (d.get('full_name'), (d.get('owner') or {}).get('login')))
    else:
        print('    body=%s' % b[:400])

print()
print('[2] 轮询 fork 就绪（最多 20 次 x 6s）')
ready = None
for i in range(20):
    time.sleep(6)
    st, b, _ = _gh.api("https://api.github.com/repos/%s" % FK)
    if st == 200:
        d = _gh.jload(b) or {}
        ready = d
        print('    [%3ds] HTTP 200  %s  default=%s  size=%sKB  pushed_at=%s' %
              ((i + 1) * 6, d.get('full_name'), d.get('default_branch'), d.get('size'), d.get('pushed_at')))
        break
    print('    [%3ds] HTTP %s' % ((i + 1) * 6, st))

if ready:
    # 确认 tag 在 fork 上（fork 会复制 refs）
    st, b, _ = _gh.api("https://api.github.com/repos/%s/git/ref/tags/v0.1.40.2" % FK)
    d = _gh.jload(b) or {}
    print()
    print('[3] fork 上 tag v0.1.40.2: HTTP %s  sha=%s' % (st, (d.get('object') or {}).get('sha', '')[:12]))
    st, b, _ = _gh.api("https://api.github.com/repos/%s/branches?per_page=5" % FK)
    brs = _gh.jload(b) or []
    print('    fork 分支: %s' % ([x.get('name') for x in brs] if isinstance(brs, list) else b[:200]))
else:
    print('!! fork 未就绪')
