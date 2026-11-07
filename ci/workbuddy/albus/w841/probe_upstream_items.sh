set +e
cd /home/albus/strata166/gfx906
echo "=== [1] 上游这几个开关在本树里存在吗（0.2.8 基底） ==="
for k in STRATA_PF_MMVQ STRATA_GFX906_TOPK_SPLIT STATTR_PREFILL_ROUTED_STREAM STRATA_PREFILL_ROUTED_STREAM STRATA_SELECT_SIMT STRATA_ROUTE_WIN multi_block_head_ops argmax_rows_wanted; do
  printf '%-34s %s\n' "$k" "$(grep -rn "$k" src include 2>/dev/null | wc -l)"
done
echo
echo "=== [2] --prompt-cache-every 的钳位逻辑 ==="
grep -rn "prompt_cache_every\|prompt-cache-every" src/program/generate.cpp serve/*.py 2>/dev/null | head -20
echo
echo "=== [3] 生产日志里的前缀复用 ==="
docker exec strata166-407 bash -lc "grep -aE 'tokens = [0-9]+ reused|[0-9]+ reused' /data/strata-huihui-ud-iq4_xs.log | tail -8"
echo
echo "=== [4] KV/缓存相关启动行 ==="
docker exec strata166-407 bash -lc "grep -aiE 'vram reserve|checkpoint every|conversation cache:' /data/strata-huihui-ud-iq4_xs.log | tail -6"
