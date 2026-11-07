#!/bin/bash
# W856 / R17：第三条支线 gfx906/mmq-plan-banner —— 给 mmq_plan 加一行无条件 banner（三路层数）
set -u
cd /home/albus/strata166/gfx029
if [ ! -d /home/albus/strata166/gfx-mmq ]; then
  git worktree add -B gfx906/mmq-plan-banner /home/albus/strata166/gfx-mmq aef9d256
fi
cd /home/albus/strata166/gfx-mmq || exit 1
python3 - <<'PY'
import io
p = 'src/prefill/prefill.cpp'
s = io.open(p, encoding='utf-8').read()
anchor = "        // STRATA_MMQ_DIRECT=1: a native layer's resident experts are read in place when the pointer-table MMQ covers"
add = '''        {   // W856 / R17: which layers take which expert path (one unconditional line; the plan is taken once)
            int64_t n_mmq = 0, n_fo = 0, n_fp16 = 0;
            for (int64_t l = 0; l < layers; ++l) {
                if (p.layer[(size_t) l]) ++n_mmq;
                else if (p.fo[(size_t) l]) ++n_fo;
                else ++n_fp16;
            }
            std::fprintf(stderr, "strata: prompt experts: MMQ %lld / fused %lld / FP16 %lld of %lld layers%s\\n",
                         (long long) n_mmq, (long long) n_fo, (long long) n_fp16, (long long) layers,
                         p.fallback ? " (some layer falls back)" : " (no fallback)");
        }
'''
if 'W856 / R17' in s:
    print('already patched')
else:
    assert anchor in s, 'anchor missing'
    s = s.replace(anchor, add + anchor)
    io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
    print('patched')
PY
cd /home/albus/strata166/gfx-mmq && git diff --stat
