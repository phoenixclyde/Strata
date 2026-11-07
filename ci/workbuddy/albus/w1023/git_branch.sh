#!/bin/bash
# Move the b12129 port off the mainline: the branch must keep compiling against b11062.
set -euo pipefail
cd /home/albus/strata166/pr/strata-fork

echo "=== dirty before:"
git status --porcelain

git checkout -q -b exp/lcpp-b12129
git add -A

cat > /tmp/msg_b12129.txt <<'EOF'
exp: port to llama.cpp b12129 (compiles; 4% slower on gfx906, not adopted)

b12129 needs four ports, all mechanical:
  ggml_cuda_mmq_get_config(type, J, fallback, cc)   -> + prec_src1        (5 sites)
  mul_mat_q_case<type>(ctx, args, s)               -> <type, prec_src1>  (24 sites)
  new_pool_for_device(int, int)                    -> (context &, int, int)
  DECL_MMQ_CASE(NVFP4) in the W4A4 TU              -> DECL_MMQ_CASE_W4A4

The full tree compiles against b12129 (b11062's iqp.cpp is gone; nothing referenced it)
and the binary runs, but the measurement is a regression:

  prefill@2K   530.43 -> 509.11  (-4.02%, CV 0.75%)
  prefill@8K   716.02 -> 683.13  (-4.59%, CV 0.26%)
  prefill@16K  780    -> 766.02  (-1.79%, CV 0.08%)
  decode        33.64 -> 35.48   (+5.5%, inside CV 3.97%)

Numerics: a 48-token greedy fingerprint is byte-identical on the 968-token English
prompt and shares the prefix on the other two (they differ only at the token budget),
so the MoE layout change did not break the prefill arithmetic.

The 1.23x llama.cpp #31047 reports on MI50 is Q4_0 through mmid's new tile assignment;
our experts are Q4_K/Q5_K and moe_mmq builds its own expert bounds, so that path never
runs.  The mechanism behind the -4% is NOT established -- this branch exists so the next
attempt starts from "it compiles", not from zero.
EOF

git -c user.name=albus -c user.email=a@b commit -q -F /tmp/msg_b12129.txt
git log --oneline -1

git checkout -q gfx906/mi50
echo "=== dirty after (want 0):"
git status --porcelain | wc -l
echo "=== branches:"
for b in gfx906/mi50 exp/lcpp-b12129; do printf "%-16s %s\n" "$b" "$(git rev-parse --short $b)"; done
