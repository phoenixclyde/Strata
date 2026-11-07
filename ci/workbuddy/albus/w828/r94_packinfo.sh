echo "--- pack dir ---"
ls -la /home/albus/strata166/data/packs/ud-q4_k_xl | head -20
echo "--- metadata files ---"
for f in /home/albus/strata166/data/packs/ud-q4_k_xl/*.json /home/albus/strata166/data/packs/ud-q4_k_xl/*.txt; do
  [ -f "$f" ] && echo "== $f" && head -c 600 "$f" && echo
done
echo "--- du ---"
du -sh /home/albus/strata166/data/packs/ud-q4_k_xl
echo "--- gguf tensor types of the source model (first shard) ---"
ls -la /models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/unsloth-UD-Q4_K_XL/ 2>/dev/null | head
