import difflib
import sys

BASE = 'D:/workbuddy_space/strata_ws/albus/w827/up/'
pairs = {
    's2': ('src__kernels__cuda__s2_expert_grouped.cu',),
    'vfy': ('src__kernels__cuda__verify_kernels.cu',),
    'es': ('src__core__expert_source.cpp',),
    'cc': ('include__strata__core__conversation_cache.hpp',),
}


def show(prefix, ctx=6, maxlines=4000):
    stem = pairs[prefix][0]
    a = open(BASE + stem + '.v0271', encoding='utf-8', errors='replace').read().split('\n')
    b = open(BASE + stem + '.v028', encoding='utf-8', errors='replace').read().split('\n')
    d = list(difflib.unified_diff(a, b, 'v0271/' + stem, 'v028/' + stem, n=ctx, lineterm=''))
    print('#### %s  (%d diff lines)' % (stem, len(d)))
    for l in d[:maxlines]:
        print(l)


for p in sys.argv[1:]:
    show(p)
