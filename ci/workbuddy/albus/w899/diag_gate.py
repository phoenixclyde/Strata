"""R54 diagnostic: prove whether the persistent kernel is actually entered.

B arm measured the same as A, and nothing in the log showed the kernel.  Two possibilities:
the gate never passes (`g_mk_cnt` still null because Verifier::init is not the path taken, or a
side branch is on), or it runs and simply does not pay.  This prints the gate's inputs once and a
call/enter tally every 250 calls, so the next run answers it from the engine's own log.
"""
import shutil
import sys
from pathlib import Path

V = Path('/home/albus/strata166/work/r54/src/core/verify.cpp')
BAK = V.with_suffix('.cpp.diagbak')
if not BAK.exists():
    shutil.copy2(V, BAK)

v = V.read_text(encoding='utf-8')
anchor = '                if (mk_on) {\n'
diag = '''                {   // R54 diagnostic: is the persistent kernel entered at all?
                    static long mk_n = 0, mk_on_n = 0;
                    static bool said = false;
                    if (!said && n >= 2) {
                        said = true;
                        std::fprintf(stderr,
                                     "R54 gate: n=%d tb=%d te=%d batch=%d side_proj=%d br=%d sidem=%d prof=%d cnt=%p on=%d\\n",
                                     (int) n, (int) tb, (int) te, (int) batch_rec_, (int) side_proj, (int) br,
                                     (int) sidem, (int) prof_on_, (void*) g_mk_cnt, (int) mk_on);
                    }
                    if (mk_on) ++mk_on_n;
                    if (++mk_n % 250 == 0) std::fprintf(stderr, "R54 calls=%ld on=%ld\\n", mk_n, mk_on_n);
                }
'''
if v.count(anchor) != 1:
    print('anchor count', v.count(anchor))
    sys.exit(2)
v = v.replace(anchor, diag + anchor)
V.write_text(v, encoding='utf-8')
print('diag inserted')
