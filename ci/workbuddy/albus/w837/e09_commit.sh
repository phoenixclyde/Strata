#!/bin/bash
# W837: commit the gfx906 arch entry onto our branch and push
set -e
F=/home/albus/strata166/pr/strata-fork
W=/home/albus/strata166/gfx906
cd $F || exit 1
git checkout gfx906/0.2.8-mi50 2>&1 | tail -1

for f in include/strata/kernels/gfx_arch.hpp include/strata/core/arch_defaults.hpp \
         src/core/arch_defaults.cpp src/core/arch_defaults_test.cpp; do
  cp -a "$W/$f" "$f"
done

echo "=== diff summary ==="
git diff --stat

echo
echo "=== the exact table, as committed ==="
git diff -U1 -- src/core/arch_defaults.cpp | grep -E '^\+' | grep -vE '^\+\+\+' | head -30

git add include/strata/kernels/gfx_arch.hpp include/strata/core/arch_defaults.hpp \
        src/core/arch_defaults.cpp src/core/arch_defaults_test.cpp
git commit -q -F - <<'MSG'
gfx906: give the architecture a per-card entry (predicate + exact table + opt-in recipe)

Until now gfx906 had no entry anywhere: arch_defaults.cpp returned an empty
table at the `if (!gfx_arch_is_gfx1151) return t;` line, and gfx_arch.hpp had
predicates for gfx11_wmma / gfx12 / gfx1151 but none for gfx906 -- the card was
only ever recognised by ad-hoc string compares inside kernels.  Two switches
written FOR this card (STRATA_GFX906_ATTN_REDUCE12, STRATA_GFX906_ATTN_QUERY_SWIZZLE)
therefore defaulted to off: a user who does not know them gets neither.

This is the same shape gfx1151 and gfx12 use, split the same way -- exact
switches in the default table, rounding-level switches in an opt-in set:

* gfx_arch_is_gfx906() -- the predicate, next to the other four.
* arch_default_env("gfx906") -> two switches, both measured BYTE-IDENTICAL on
  an MI50 here, so there is nothing to gate:
    - STRATA_GDN_HEAD=1      LOGPOS gate: KL mean 0.0000, argmax 100%,
                             top-10 1.00, mean |dlp| 0.00000
    - STRATA_GFX906_ATTN_REDUCE12=1   three whole LOGPOS dumps of the same
                             prompts are md5-identical with it on and off
  STRATA_GFX906_DEFAULTS=0 turns the table off; STRATA_DEFAULTS=026 returns
  nothing (0.2.6 had no gfx906 table to restore).
* gfx906_tuned_env() -> the seven switches the production MI50 build runs that
  DO change bits, so they stay opt-in behind STRATA_GFX906_TUNED=1:
    QUERY_SWIZZLE 1, GDN_PP 2, HC_Q8 1 (KL 0.0011), SELECT_SIMT 1 (0.0004),
    ROUTE_TAIL_SKIP 7 (0.0008), MMQ_KQ 1 (0.0171, +68% prompt throughput),
    HIP_PROMPT_F16 1 (0.0026, ~1.6x prompt throughput)
  The KL figures are per-switch teacher-forced measurements against this same
  engine, not a claim that they add up (they do not: the five-switch total is
  0.0293 while the per-switch sum is 0.0062).

A switch the user set is never overridden: apply_arch_defaults checks getenv
first, which the test asserts.  The banner now names gfx906 instead of falling
through to the gfx1151 wording.

Tested: arch_defaults_test passes with all pre-existing gfx1151 / gfx12 / igpu
assertions unchanged (18 and 9 exact switches respectively), plus new gfx906
cases -- table contents, "no bit-changing switch in the exact table", the
defaults-026 and DEFAULTS=0 paths, the tuned set being opt-in and gfx906-only,
and the suffix form gfx906:sramecc-:xnack-.
MSG

echo
echo "=== push ==="
git push origin gfx906/0.2.8-mi50 2>&1 | tail -4
echo
git log --oneline ghup/main..HEAD | head -3
git diff --stat ghup/main..HEAD | tail -3
