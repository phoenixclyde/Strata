import io, sys

W = '/home/albus/strata166/gfx906/'

# ---------------------------------------------------------------- 1) predicate
p = W + 'include/strata/kernels/gfx_arch.hpp'
s = io.open(p, encoding='utf-8').read()
anchor = '''/// Strix Halo (Ryzen AI Max, RDNA3.5): the part the gfx1151 defaults (docs/STRIX_HALO.md) are measured on.'''
add = '''/// gfx906 (MI50 / MI60 / Radeon VII, Vega 20): 64-lane waves, no MFMA, no native bf16.  The part the gfx906 default
/// table, the 12-head attention reduction and the q-side swizzle are written for.  Note that `v_dot2_f32_f16`,
/// `v_dot4_i32_i8` and `v_dot8_i32_i4` ARE available here (verified with llvm-mc --mcpu=gfx906); only the
/// saturating forms (*c) and v_mfma are not.
inline bool gfx_arch_is_gfx906(const char* gcn) { return gfx_arch_is(gcn, "gfx906"); }

'''
assert s.count(anchor) == 1, ('predicate anchor', s.count(anchor))
s = s.replace(anchor, add + anchor, 1)
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('1/4 predicate added')

# ---------------------------------------------------------------- 2) header decl
p = W + 'include/strata/core/arch_defaults.hpp'
s = io.open(p, encoding='utf-8').read()
anchor = '''/// The integrated Radeons'''
add = '''/// gfx906 (MI50 / MI60 / Radeon VII): the switches this card's measured recipe uses that DO change bits, so they
/// cannot sit in the exact table -- the same split gfx1151 makes.  Empty unless STRATA_GFX906_TUNED=1, and empty when
/// STRATA_GFX906_DEFAULTS=0.  A switch the user set is never overridden (apply_arch_defaults checks first).
std::vector<std::pair<std::string, std::string>> gfx906_tuned_env(const char* gcn_arch);

'''
assert s.count(anchor) == 1, ('header anchor', s.count(anchor))
s = s.replace(anchor, add + anchor, 1)
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('2/4 header declaration added')

# ---------------------------------------------------------------- 3) impl
p = W + 'src/core/arch_defaults.cpp'
s = io.open(p, encoding='utf-8').read()

anchor = '    if (!strata::kernels::gfx_arch_is_gfx1151(gcn_arch)) return t;'
block = '''    // gfx906 (MI50 / MI60 / Radeon VII, Vega 20): the two switches on this branch that are measured BYTE-IDENTICAL
    // here, so they are on by default on this card and nowhere else.  Everything else this card's recipe uses changes
    // bits and lives in gfx906_tuned_env() below (STRATA_GFX906_TUNED=1) -- the same exact/rounding split the gfx1151
    // table makes, and the reason this table has two entries instead of fourteen.
    if (strata::kernels::gfx_arch_is_gfx906(gcn_arch)) {
        const char* off906 = std::getenv("STRATA_GFX906_DEFAULTS");
        if (off906 != nullptr && off906[0] == '0') return t;
        if (defaults026) return t;   // STRATA_DEFAULTS=026: 0.2.6 had no gfx906 table, so there is nothing to restore
        t = {
            // The GDN recurrence with four lanes a column plus the grid-stride norm (S23; the same kernel the gfx11
            // table takes first).  Measured on one MI50 with the teacher-forced LOGPOS gate: KL mean 0.0000,
            // median 0, argmax agreement 100%, top-10 1.00, mean |dlp| 0.00000 -- bitwise.
            {"STRATA_GDN_HEAD", "1"},
            // The 12 query heads' lane sums reduced with 16 shuffle exchanges instead of 60 (the gfx906 kernel that
            // upstream #1661 gated to kv_mode 1).  Three whole LOGPOS dumps of the same prompts are byte-identical
            // with it on and off (md5 equal), so this is an exact reordering, not a rounding change.
            {"STRATA_GFX906_ATTN_REDUCE12", "1"},
        };
        return t;
    }
'''
assert s.count(anchor) == 1, ('impl anchor', s.count(anchor))
s = s.replace(anchor, block + anchor, 1)

# the tuned set, placed right after the table function
anchor2 = '''static void set_default(const std::pair<std::string, std::string>& kv) {'''
tuned = '''// gfx906's rounding-level recipe: the switches the production MI50 build runs that are NOT byte-identical, so they
// cannot be defaults.  Opt-in as a set (STRATA_GFX906_TUNED=1) because they interact: the KL figures below are the
// teacher-forced LOGPOS measurement of each switch against this same engine, not a claim that they add up.
std::vector<std::pair<std::string, std::string>> gfx906_tuned_env(const char* gcn_arch) {
    std::vector<std::pair<std::string, std::string>> t;
    if (!strata::kernels::gfx_arch_is_gfx906(gcn_arch)) return t;
    const char* off = std::getenv("STRATA_GFX906_DEFAULTS");
    if (off != nullptr && off[0] == '0') return t;
    const char* on = std::getenv("STRATA_GFX906_TUNED");
    if (on == nullptr || on[0] != '1') return t;
    t = {
        // the q-side LDS bijection: permutes whole 16-dimension groups of the query rows inside LDS, so every
        // reduction sums the same values in the same order.  Not yet md5-gated here (it is on in production).
        {"STRATA_GFX906_ATTN_QUERY_SWIZZLE", "1"},
        // two columns per lane in the GDN recurrence (the gfx1151 table's second entry).  Not separately gated here.
        {"STRATA_GDN_PP", "2"},
        // the hyper-connection projections read as the GGUF's own Q8_0 bytes: KL 0.0011, argmax 100%
        {"STRATA_HC_Q8", "1"},
        // the FP32 tiled block scorer: KL 0.0004, argmax 100%
        {"STRATA_SELECT_SIMT", "1"},
        // skip the experts that rank below 7 in a window nobody routes to: KL 0.0008, argmax 100%
        {"STRATA_ROUTE_TAIL_SKIP", "7"},
        // the K-quant prompt kernels.  KL 0.0171 with argmax still 100%, and worth +68% prompt throughput here
        // (the largest single lever found on this card): opt-in for the KLD reason, not the speed reason.
        {"STRATA_MMQ_KQ", "1"},
        // the prompt's 16-bit GEMMs run FP16 in and out: KL 0.0026, and about 1.6x the prompt throughput
        {"STRATA_HIP_PROMPT_F16", "1"},
    };
    return t;
}

'''
assert s.count(anchor2) == 1, ('tuned anchor', s.count(anchor2))
s = s.replace(anchor2, tuned + anchor2, 1)

# apply them
anchor3 = '''    std::vector<std::string> igpu;'''
body = '''    std::vector<std::string> tuned;
    for (const auto& kv : gfx906_tuned_env(gcn_arch)) {
        if (std::getenv(kv.first.c_str()) != nullptr) continue;   // the user's setting wins, whatever it is
        set_default(kv);
        tuned.push_back(kv.first);
    }
    if (!tuned.empty()) {
        std::fprintf(stderr, "strata: gfx906 (MI50-class): the rounding-level recipe is on (STRATA_GFX906_TUNED=0 turns it off; "
                             "each switch of it is separate): ");
        for (size_t i = 0; i < tuned.size(); ++i) std::fprintf(stderr, "%s%s", i ? " " : "", tuned[i].c_str() + 7);
        std::fprintf(stderr, "\\n");
    }
'''
assert s.count(anchor3) == 1, ('apply anchor', s.count(anchor3))
s = s.replace(anchor3, body + anchor3, 1)

# the banner printed for the exact table names only two architectures; make it three
old_banner = '''        const bool g12 = strata::kernels::gfx_arch_is_gfx12(gcn_arch);
        std::fprintf(stderr, "strata: %s: %zu exact speed switches on by default (%s=0 turns "
                             "them off; a switch you set is kept): ",
                     g12 ? "gfx12 (RDNA4)" : "gfx1151 (Strix Halo)", set.size(),
                     g12 ? "STRATA_GFX12_DEFAULTS" : "STRATA_GFX1151_DEFAULTS");'''
new_banner = '''        const bool g12 = strata::kernels::gfx_arch_is_gfx12(gcn_arch);
        const bool g9 = strata::kernels::gfx_arch_is_gfx906(gcn_arch);
        std::fprintf(stderr, "strata: %s: %zu exact speed switches on by default (%s=0 turns "
                             "them off; a switch you set is kept): ",
                     g9 ? "gfx906 (MI50-class)" : g12 ? "gfx12 (RDNA4)" : "gfx1151 (Strix Halo)", set.size(),
                     g9 ? "STRATA_GFX906_DEFAULTS" : g12 ? "STRATA_GFX12_DEFAULTS" : "STRATA_GFX1151_DEFAULTS");'''
assert s.count(old_banner) == 1, ('banner', s.count(old_banner))
s = s.replace(old_banner, new_banner, 1)

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('3/4 implementation added')
