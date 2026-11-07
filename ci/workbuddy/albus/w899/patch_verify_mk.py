"""R54 integration (branch r54-port only): call the persistent GDN kernel when it owns the layer.

Every anchor is asserted to be unique before it is touched; the file is backed up first.
The gate is n >= 4 (T=1 -10.9%, T=2 -9.6%, T=3 -0.9%, T=4 +12.7%, T=5 +15.1%, T=6 +16.6%,
W899 7.4) plus "no side branch, no per-slot batch, no profiling" - the kernel runs the whole
chain on one stream and cannot share the layer with the side projections.
"""
import shutil
import sys
from pathlib import Path

P = Path('/home/albus/strata166/work/r54/src/core/verify.cpp')
BAK = P.with_suffix('.cpp.r54bak')

INC_OLD = '#include "strata/kernels/iq_kernels.hpp"'
INC_NEW = INC_OLD + '\n#include "strata/kernels/megakernel.hpp"'

LAUNCH_OLD = '                if (!q8_attn) quant_in(xm, (int) N);\n                if (side_proj) {   // the gate projection'
LAUNCH_NEW = '''                // ---- R54: the GDN chain as one persistent kernel (W899 7) -------------------------
                // Only when it owns the layer: the six kernels are faster at n <= 3 (T=1 -10.9%,
                // T=3 -0.9%; T=4 +12.7%, T=5 +15.1%), and the kernel is bitwise equal to them
                // (mk_gdn_parity: 0 differing values at T=1..8).  STRATA_MK_GDN=1 opts in.
                static const bool mk_env = [] {
                    const char* e = std::getenv("STRATA_MK_GDN");
                    return e != nullptr && std::atoi(e) != 0;
                }();
                static unsigned* mk_cnt = nullptr;
                const bool mk_on = mk_env && n >= 4 && tb == 0 && te == n && !batch_rec_ && !side_proj &&
                                   !br && !sidem && !prof_on_;
                if (mk_on) {
                    if (mk_cnt == nullptr) mk_cnt = strata::kernels::mk_counters_alloc();
                    strata::kernels::MkGdnArgs mk;
                    mk.x = xm;
                    mk.xq = xq_;                          // phase 3 overwrites it with y's image, as the
                    mk.yq = xq_;                          // six-kernel path does under STRATA_QFUSE
                    mk.w_qkv = wqkv->native_data;
                    mk.w_z = wg->native_data;
                    mk.w_out = wout->native_data;
                    mk.qkv = qkv;
                    mk.z = z_;
                    mk.hist = conv;
                    mk.w_conv = (const float*) wc->data;
                    mk.h = hb;
                    mk.w_alpha = (const uint16_t*) wa->data;
                    mk.w_beta = (const uint16_t*) wb->data;
                    mk.dt = (const float*) wdt->data;
                    mk.ssm_a = (const float*) wsa->data;
                    mk.gate = gate;
                    mk.beta = beta;
                    mk.state = state;
                    mk.gamma = (const float*) wnm->data;
                    mk.y = y_;
                    mk.bo = bo_;
                    mk.n_embd = (int) N;
                    mk.conv_channels = (int) C;
                    mk.value_dim = (int) ZV;
                    mk.h_k = (int) HK;
                    mk.h_v = (int) HV;
                    mk.eps = EPS;
                    mk.counters = mk_cnt;
                    mk.diag = q8_attn ? 32 : 0;           // xq_ already holds the input's q8_1
                    strata::kernels::mk_gdn_dense(mk, (int) n, cs);
                    il_ready = false;                     // xq_ no longer holds x's image
                }
                if (!mk_on && !q8_attn) quant_in(xm, (int) N);
                if (side_proj) {   // the gate projection'''

REPL = [
    ('                if (!side_proj) mm(wqkv, qkv + (size_t) tb * C, (int) N, (int) C);',
     '                if (!mk_on && !side_proj) mm(wqkv, qkv + (size_t) tb * C, (int) N, (int) C);'),
    ('                if (batch_rec_) {   // contiguous rows may be proposals for the same slot',
     '                if (mk_on) {        // R54: the persistent kernel ran the whole chain\n'
     '                } else if (batch_rec_) {   // contiguous rows may be proposals for the same slot'),
    ('                if (!fuse_ab && !sidem)',
     '                if (!mk_on && !fuse_ab && !sidem)'),
    ('                if (!side_proj) mm(wg, z_ + (size_t) tb * ZV, (int) N, (int) ZV);',
     '                if (!mk_on && !side_proj) mm(wg, z_ + (size_t) tb * ZV, (int) N, (int) ZV);'),
    ('                } else\n                gdn_step_norm_multi(state, hb,',
     '                } else if (!mk_on)\n                gdn_step_norm_multi(state, hb,'),
    ('                if (!g_qfuse() || batch_rec_) quant_in(y_ + (size_t) tb * ZV, (int) ZV);',
     '                if (!mk_on && (!g_qfuse() || batch_rec_)) quant_in(y_ + (size_t) tb * ZV, (int) ZV);'),
    ('                mm(wout, bo_ + tb * N, (int) ZV, (int) N);',
     '                if (!mk_on) mm(wout, bo_ + tb * N, (int) ZV, (int) N);'),
]

text = P.read_text(encoding='utf-8')
orig = text

for old, new in [(INC_OLD, INC_NEW), (LAUNCH_OLD, LAUNCH_NEW)] + REPL:
    n = text.count(old)
    if n != 1:
        print('ANCHOR COUNT %d for: %s' % (n, old.splitlines()[0][:80]))
        sys.exit(2)
    text = text.replace(old, new)

if text == orig:
    print('no change')
    sys.exit(3)

if not BAK.exists():
    shutil.copy2(P, BAK)
P.write_text(text, encoding='utf-8')
print('patched; mk_on sites:', text.count('mk_on'), 'backup:', BAK)
