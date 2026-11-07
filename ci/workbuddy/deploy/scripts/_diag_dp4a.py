# -*- coding: utf-8 -*-
"""核实 gfx906 上 __dp4a 的两条路径：我们这版走的是 sdot4（硬件）还是 4 次循环（退化）。"""
import os, re, sys
sys.stdout.reconfigure(encoding='utf-8')

TREES = {
    '0.1.39': r'D:\Strata\src\Strata-0.1.39',
    '0.1.40.1': r'D:\strata166\tmp\src401_pristine\Strata-0.1.40.1',
}
NEEDLES = ['dp4a', 'sdot4', 'v_dot4_i32_i8', 'udot4', 'dot4']

for tag, root in TREES.items():
    print('#' * 78)
    print('## %s' % tag)
    print('#' * 78)
    for r, d, fs in os.walk(os.path.join(root, 'include')):
        for f in sorted(fs):
            if not f.endswith(('.h', '.hpp', '.cuh')):
                continue
            p = os.path.join(r, f)
            s = open(p, encoding='utf-8', errors='replace').read()
            if not any(n in s for n in NEEDLES):
                continue
            rel = os.path.relpath(p, root)
            hits = [(i, ln) for i, ln in enumerate(s.splitlines(), 1)
                    if any(n in ln for n in NEEDLES)]
            print('  --- %s  (%d 命中行) ---' % (rel, len(hits)))
            for i, ln in hits[:22]:
                print('    %-5d %s' % (i, ln.strip()[:150]))
            print()
