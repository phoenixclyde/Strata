set +e
IMG=strata-gfx906:0.2.9t2
docker run --rm --entrypoint bash "$IMG" -lc '
T=/opt/rocm/core-7.14/share/hipblaslt/tensilelite/Tensile
echo "===== [1] TensileLite 版本与 SupportedISA ====="
grep -n "SupportedISA" -A 12 $T/Common.py 2>/dev/null | head -20
echo
echo "===== [2] 生成器里 MFMA 依赖的规模 ====="
echo -n "  Components 文件数: "; ls $T/Components/*.py 2>/dev/null | wc -l
echo -n "  提到 mfma 的文件数: "; grep -rli "mfma" $T/Components/*.py 2>/dev/null | wc -l
echo -n "  提到 mfma 的行数: "; grep -ri "mfma" $T/Components/*.py 2>/dev/null | wc -l
echo -n "  提到 v_dot2/dot2 的文件数: "; grep -rli "dot2" $T/Components/*.py 2>/dev/null | wc -l
echo
echo "===== [3] 关键：asm 里 gfx90a+ 才有的 directive 从哪来 ====="
grep -rn "amdhsa_accum_offset\|AccumOffset\|accum_offset" $T/Components/*.py $T/*.py 2>/dev/null | head -8
echo
echo "===== [4] 有没有 \"non-MFMA\" / VALU 路径（gfx906 需要的） ====="
grep -rn "VALU\|isVega\|gfx906\|GFX906" $T/Components/*.py 2>/dev/null | head -12
echo
echo "===== [5] Logic 目录结构（有没有 vega20 / gfx906） ====="
ls $T/Logic 2>/dev/null | head -14
echo "  --- 子目录里的 arch:"; find $T/Logic -maxdepth 2 -type d 2>/dev/null | head -12
'
