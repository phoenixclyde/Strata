import io

W = '/home/albus/strata166/gfx906/'
p = W + 'src/core/arch_defaults_test.cpp'
s = io.open(p, encoding='utf-8').read()

anchor = '''    // gfx1151, plain and with its feature suffix: the table, and no bit-changing switch in it'''
block = '''    // gfx906 (MI50 / MI60 / Radeon VII): two exact switches, nothing rounding-level, and two ways to turn it off.
    {
        unset("STRATA_GFX906_DEFAULTS");
        unset("STRATA_GFX906_TUNED");
        auto find = [](const std::vector<std::pair<std::string, std::string>>& t, const char* k) -> const std::string* {
            for (const auto& kv : t) if (kv.first == k) return &kv.second;
            return static_cast<const std::string*>(nullptr);
        };
        for (const char* a : {"gfx906", "gfx906:sramecc-:xnack-"}) {
            const auto t = arch_default_env(a);
            CHECK(t.size() == 2);
            const std::string* head = find(t, "STRATA_GDN_HEAD");
            const std::string* red = find(t, "STRATA_GFX906_ATTN_REDUCE12");
            CHECK(head != nullptr && *head == "1");
            CHECK(red != nullptr && *red == "1");
            // nothing that changes bits may sit in the exact table
            for (const char* bits : {"STRATA_HC_Q8", "STRATA_MMQ_KQ", "STRATA_HIP_PROMPT_F16", "STRATA_SELECT_SIMT",
                                     "STRATA_ROUTE_TAIL_SKIP", "STRATA_GFX906_ATTN_QUERY_SWIZZLE", "STRATA_GDN_PP",
                                     "STRATA_PF_GEMM", "STRATA_PF_FUSED", "STRATA_HC_UPMIX", "STRATA_PA_FAST",
                                     "STRATA_HIP_WMMA", "STRATA_SELECT_WMMA"})
                CHECK(find(t, bits) == nullptr);
            // 026 restores 0.2.6, which had no gfx906 table
            CHECK(arch_default_env(a, true, false).empty());
            // the tuned set is opt-in and never in the exact table
            CHECK(gfx906_tuned_env(a).empty());
        }
        // the switch suffix of another arch must not be mistaken for gfx906
        CHECK(arch_default_env("gfx9060").empty());
        // STRATA_GFX906_DEFAULTS=0 turns the exact table off
        put("STRATA_GFX906_DEFAULTS", "0");
        CHECK(arch_default_env("gfx906").empty());
        CHECK(gfx906_tuned_env("gfx906").empty());
        unset("STRATA_GFX906_DEFAULTS");
        // STRATA_GFX906_TUNED=1 brings the rounding-level set, and only for gfx906
        put("STRATA_GFX906_TUNED", "1");
        const auto tuned = gfx906_tuned_env("gfx906");
        CHECK(tuned.size() == 7);
        for (const char* k : {"STRATA_GFX906_ATTN_QUERY_SWIZZLE", "STRATA_GDN_PP", "STRATA_HC_Q8", "STRATA_SELECT_SIMT",
                              "STRATA_ROUTE_TAIL_SKIP", "STRATA_MMQ_KQ", "STRATA_HIP_PROMPT_F16"})
            CHECK(find(tuned, k) != nullptr);
        CHECK(gfx906_tuned_env("gfx1151").empty());
        CHECK(gfx906_tuned_env("gfx1201").empty());
        unset("STRATA_GFX906_TUNED");
    }

'''
assert s.count(anchor) == 1, ('test anchor', s.count(anchor))
s = s.replace(anchor, block + anchor, 1)

# the "other architectures get nothing" list must not include gfx906 any more
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('4/4 test added')

# sanity: gfx906 must not be in the "empty for other architectures" assertions
for line in s.split('\n'):
    if 'arch_default_env("gfx906' in line:
        print('   check line:', line.strip()[:110])
