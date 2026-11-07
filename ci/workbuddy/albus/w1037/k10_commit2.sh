#!/bin/bash
set -u
WT=/home/albus/strata166/pr/k10
R=/home/albus/strata166/tmp/w1037
B=/home/albus/strata166/data/bin
MSG=$R/k10_commit_msg.txt

cat > "$MSG" <<'EOF'
gfx906: move the llama.cpp pin to b12110 + mmq@4c1004c (K10) on the 0.2.11 tree

K10 was measured free on 2026-11-07 (534.83/716.72 vs 532.76/714.89) but its source tree was lost,
so this re-derives it from upstream and records what moving the pin actually costs:

  * mul_mat_q_case<type> -> <type, GGML_PREC_Q8>        (llama.cpp #30168)  25 call sites
  * ggml_cuda_mmq_get_config(.., cc) -> (.., cc, GGML_PREC_Q8)              5 call sites
  * ggml_backend_cuda_context::new_pool_for_device gains a ctx argument     1 definition
  * cmake/strata_ggml_tq_overlay.cmake: probe the write-back signature instead of
    inferring the extra bool argument from get_nthreads (b12110 dropped it)

llama tree = ref/llama_b12110 + ggml/src/ggml-cuda/mmq* from 4c1004c49221b07c3b8108977e3d1991fc9f45cc (2026-10-19)
binary     = build-k10p/strata  e0a6987f732a401f780f5dad5812812f  43,207,464 B (TQ overlay ON)
EOF

cd "$WT" || exit 1
git checkout -q -B gfx906/lcpp-k10 || exit 1
git add -A cmake/strata_ggml_tq_overlay.cmake src/prefill/ggml_cuda_host.cu src/prefill/mmq_kq_lib.cu \
          src/prefill/mmq_nvfp4_w4a4.cu src/prefill/mmq_nvfp4_w4a8.cu src/prefill/moe_mmq.cu || exit 1
git -c user.name=albus -c user.email=albus@localhost commit -q -F "$MSG" || exit 1
git log --oneline -2
echo "dirty=$(git status --porcelain | wc -l)"

cp -f /home/albus/strata166/build-k10p/strata "$B/strata-0.1.57-k10p.new" || exit 1
chmod 755 "$B/strata-0.1.57-k10p.new"
mv -f "$B/strata-0.1.57-k10p.new" "$B/strata-0.1.57-k10p" || exit 1
md5sum "$B/strata-0.1.57-k10p"
ls -l "$B/strata-0.1.57-k10p"
