import sys, base64, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'w820'))
from gh import api

FILES = [
    'CMakeLists.txt',
    'src/core/nv_defaults.cpp',
    'include/strata/core/nv_defaults.hpp',
    'src/kernels/cpu/portable.cpp',
    'src/prefill/moe_fused_iq.cu',
]
os.makedirs('albus/w824/up0271', exist_ok=True)
for f in FILES:
    d = api('/repos/Niko1221/Strata/contents/%s?ref=v0.2.7.1' % f, timeout=240)
    raw = base64.b64decode(d['content'])
    p = 'albus/w824/up0271/' + f.replace('/', '__')
    open(p, 'wb').write(raw)
    print('%-42s %8d bytes' % (f, len(raw)))
