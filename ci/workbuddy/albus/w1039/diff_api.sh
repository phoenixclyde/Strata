#!/bin/bash
S=/home/albus/strata166
echo "=== diff 四个文件：k10(已适配) vs port-all ==="
for f in src/prefill/moe_mmq.cu src/prefill/mmq_kq_lib.cu src/prefill/mmq_nvfp4_w4a8.cu src/prefill/ggml_cuda_host.cu; do
  echo "--- $f"
  if [ -f "$S/pr/k10/$f" ] && [ -f "$S/pr/port-all/$f" ]; then
    diff -u "$S/pr/port-all/$f" "$S/pr/k10/$f" | head -80
    echo "   (diff lines: $(diff "$S/pr/port-all/$f" "$S/pr/k10/$f" | wc -l))"
  else
    echo "   missing on one side"
  fi
done
