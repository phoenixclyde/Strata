"""R54 integration fix #1: the megakernel's counters must be allocated OUTSIDE the stream capture.

The A/B arm B died at the warm-up with `mk_gdn_dense: invalid arguments` (three times), which that
function prints when `counters == nullptr`: mk_counters_alloc() calls cudaMalloc, and the layer runs
inside cudaStreamBeginCapture (verify.cpp:2648/2800/3795/3838), where host allocation is not allowed.
So: allocate once in Verifier::init (no capture there), pass that pointer in, and never exit(1).
"""
import shutil
import sys
from pathlib import Path

V = Path('/home/albus/strata166/work/r54/src/core/verify.cpp')
M = Path('/home/albus/strata166/work/r54/src/kernels/cuda/megakernel_gdn.cu')

for p in (V, M):
    bak = p.with_suffix(p.suffix + '.fix1bak')
    if not bak.exists():
        shutil.copy2(p, bak)

v = V.read_text(encoding='utf-8')
edits = []

# 1) a file-scope pointer, allocated by init
old_inc = '#include "strata/kernels/megakernel.hpp"'
new_inc = (old_inc +
           '\n\n// R54: the persistent GDN kernel\'s phase counters.  They must be allocated BEFORE any window is\n'
           '// captured: mk_counters_alloc() calls cudaMalloc, which a capture rejects (the first A/B arm died\n'
           '// with "mk_gdn_dense: invalid arguments" because of it).\n'
           'static unsigned* g_mk_cnt = nullptr;')
edits.append((v, old_inc, new_inc, 'include'))

# 2) allocate in Verifier::init, where the window's buffers are taken (outside capture)
old_buf = '        mixed_ = b.take<float>(T * N); bo_ = b.take<float>(T * N);'
new_buf = (old_buf +
           '\n        if (g_mk_cnt == nullptr) g_mk_cnt = strata::kernels::mk_counters_alloc();   // R54 (capture-free)')
edits.append((v, old_buf, new_buf, 'init alloc'))

# 3) the layer block: no local allocation, require the pointer, use it
old_cnt = ('                static unsigned* mk_cnt = nullptr;\n'
           '                const bool mk_on = mk_env && n >= 4 &&')
new_cnt = ('                const bool mk_on = mk_env && g_mk_cnt != nullptr && n >= 4 &&')
edits.append((v, old_cnt, new_cnt, 'mk_on'))

old_alloc = '                    if (mk_cnt == nullptr) mk_cnt = strata::kernels::mk_counters_alloc();\n'
edits.append((v, old_alloc, '', 'drop local alloc'))

edits.append((v, '                    mk.counters = mk_cnt;', '                    mk.counters = g_mk_cnt;', 'counters ptr'))

for text, old, new, tag in edits:
    n = v.count(old)
    if n != 1:
        print('ANCHOR %s count=%d' % (tag, n))
        sys.exit(2)
    v = v.replace(old, new)

V.write_text(v, encoding='utf-8')

# 4) megakernel: a failure must degrade, not kill the engine
m = M.read_text(encoding='utf-8')
old1 = ('    if (n_tok < 1 || n_tok > 8 || a.counters == nullptr) { std::fprintf(stderr, "mk_gdn_dense: invalid arguments\\n"); std::exit(1); }')
new1 = ('    // R54: never std::exit here - the caller runs this inside a captured window, and an exit takes the\n'
        '    // whole engine with it (that is how the first A/B arm "hung" at the warm-up).\n'
        '    if (n_tok < 1 || n_tok > 8 || a.counters == nullptr) { std::fprintf(stderr, "mk_gdn_dense: invalid arguments\\n"); return; }')
old2 = '    if (e != cudaSuccess) { std::fprintf(stderr, "mk_gdn_dense: %s\\n", cudaGetErrorString(e)); std::exit(1); }'
new2 = '    if (e != cudaSuccess) std::fprintf(stderr, "mk_gdn_dense: %s\\n", cudaGetErrorString(e));'
for old, new in ((old1, new1), (old2, new2)):
    if m.count(old) != 1:
        print('MK ANCHOR count=%d %s' % (m.count(old), old[:60]))
        sys.exit(3)
    m = m.replace(old, new)
M.write_text(m, encoding='utf-8')
print('fix1 applied to verify.cpp and megakernel_gdn.cu')
