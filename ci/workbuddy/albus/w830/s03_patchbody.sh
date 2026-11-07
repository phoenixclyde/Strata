D=/home/albus/strata166/build024/patches
for f in patch_mmq_tile_j.py patch_gfx906_attn_swizzle.py patch_gfx906_rocblas.py patch_gr_tilev.py patch_final_ckpt.py; do
  echo "################ $f"
  head -40 "$D/$f"
  echo
done
