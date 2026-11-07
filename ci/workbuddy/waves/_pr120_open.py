# -*- coding: utf-8 -*-
"""校验分支内容 + 创建 PR"""
import sys, io, json, os, time
sys.path.insert(0, r"D:/workbuddy/_z_rk81")
sys.stdout.reconfigure(encoding='utf-8')
import _gh

UP = "Niko1221/Strata"
FK = "phoenixclyde"
BR = "gfx906-build-fixes-402"
BASE = "main"
HEAD_SHA = "87c6d0218da95a74ce3b276a255dd4372d47532b"
TAG = "e8ca9afd03d839d4f8dbbe82dffce7f8a3bafd7a"

TITLE = "hip/gfx906: the tree does not build (q6_k MMQ instance and cudaEventBlockingSync)"

# ---- 1) 校验分支 ----
st, b, _ = _gh.api("https://api.github.com/repos/%s/Strata/git/ref/heads/%s" % (FK, BR))
d = _gh.jload(b) or {}
got = (d.get('object') or {}).get('sha', '')
print('[1] branch ref: HTTP %s  sha=%s  期望=%s  %s' % (st, got[:12], HEAD_SHA[:12], 'OK' if got == HEAD_SHA else 'MISMATCH'))

st, b, _ = _gh.api("https://api.github.com/repos/%s/Strata/compare/%s...%s" % (FK, TAG, HEAD_SHA))
d = _gh.jload(b) or {}
print('[2] compare vs main: status=%s ahead_by=%s behind_by=%s  commits=%s' %
      (d.get('status'), d.get('ahead_by'), d.get('behind_by'), d.get('total_commits')))
for f in (d.get('files') or []):
    print('      %-64s %-8s +%s/-%s' % (f.get('filename'), f.get('status'), f.get('additions'), f.get('deletions')))
files = d.get('files') or []
assert len(files) == 2, '文件数应为 2，实为 %d' % len(files)
assert d.get('ahead_by') == 1, '应恰好领先 1 个 commit'

# ---- 2) 创建 PR ----
body = io.open(r"D:/strata166/pr/PR_BODY.md", encoding='utf-8').read()
print()
print('[3] 创建 PR  head=%s:%s  base=%s' % (FK, BR, BASE))
st, b, _ = _gh.api("https://api.github.com/repos/%s/pulls" % UP, method="POST",
                   payload={"title": TITLE, "body": body,
                            "head": "%s:%s" % (FK, BR), "base": BASE,
                            "draft": False, "maintainer_can_modify": True},
                   timeout=180)
d = _gh.jload(b) or {}
if st in (200, 201):
    print('    CREATED #%s' % d.get('number'))
    print('    url      = %s' % d.get('html_url'))
    print('    head     = %s @ %s' % (d['head']['label'], d['head']['sha'][:12]))
    print('    base     = %s @ %s' % (d['base']['label'], d['base']['sha'][:12]))
    print('    files=%s  +%s/-%s  commits=%s  state=%s  mergeable=%s' %
          (d.get('changed_files'), d.get('additions'), d.get('deletions'),
           d.get('commits'), d.get('state'), d.get('mergeable')))
    json.dump({"number": d.get('number'), "url": d.get('html_url'),
               "head_sha": d['head']['sha'], "base": d['base']['label']},
              open(r"D:/strata166/pr/pr_result.json", "w"), indent=2)
else:
    print('    FAILED HTTP %s' % st)
    print('    %s' % b[:900])
