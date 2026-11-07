# -*- coding: utf-8 -*-
"""查上游 Strata 最新版本，以及 gfx906 相关文件是否已修（api.github.com 在本机可用）。"""
import json, urllib.request, socket, time, re

socket.setdefaulttimeout(45)
UA = {'User-Agent': 'strata-check', 'Accept': 'application/vnd.github+json'}


def get(url, raw=False):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=45) as r:
        b = r.read()
    return b if raw else json.loads(b.decode('utf-8'))


print('=== 1) 最新 release / tag ===')
try:
    rel = get('https://api.github.com/repos/Niko1221/Strata/releases/latest')
    print('  latest release:', rel.get('tag_name'), '| published', rel.get('published_at'))
    print('  name:', (rel.get('name') or '')[:120])
except Exception as e:
    print('  FAIL', str(e)[:200])

print()
print('=== 2) 最近 tag 列表 ===')
try:
    tags = get('https://api.github.com/repos/Niko1221/Strata/tags?per_page=15')
    print('  ', ', '.join(t['name'] for t in tags))
except Exception as e:
    print('  FAIL', str(e)[:200])

print()
print('=== 3) 最近提交（看 gfx906 是否还在动）===')
try:
    cs = get('https://api.github.com/repos/Niko1221/Strata/commits?per_page=15')
    for c in cs:
        msg = c['commit']['message'].splitlines()[0]
        print('  %s  %s' % (c['sha'][:8], msg[:110]))
except Exception as e:
    print('  FAIL', str(e)[:200])

print()
print('=== 4) main 上这两个文件现在长什么样（raw 会 502，走 contents API）===')
for path in ['include/strata/platform/hip_compat/strata_hip.h',
             'src/kernels/cuda/fused_gr.cu']:
    try:
        d = get('https://api.github.com/repos/Niko1221/Strata/contents/' + path)
        import base64
        txt = base64.b64decode(d['content']).decode('utf-8', 'replace')
        print('  --- %s (%d bytes) ---' % (path, len(txt)))
        for m in re.finditer(r'^.*cudaFuncSetAttribute.*$', txt, re.M):
            print('     ', m.group(0).strip()[:170])
        # 顺带看 fused_gr 的那段是否还在
        if 'fused_gr' in path:
            for i, ln in enumerate(txt.splitlines(), 1):
                if 'cudaFuncSetAttribute' in ln:
                    print('      L%d: %s' % (i, ln.strip()[:150]))
    except Exception as e:
        print('  %s FAIL %s' % (path, str(e)[:160]))
