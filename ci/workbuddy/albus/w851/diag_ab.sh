set +e
f=$(ls -t /home/albus/strata166/data/w851_abtbl_*.txt | head -1)
echo "===== [1] 每臂 set_table 时写入的路径（脚本自己打印的） ====="
grep -a "table = /" "$f"
echo
echo "===== [2] 日志里所有 rocBLAS 行（带行号，看每次启动的实际行数） ====="
docker exec strata166-407 bash -lc "grep -an 'rocBLAS tuning enabled\|rocBLAS version mismatch\|cannot open rocBLAS' /data/strata-huihui-ud-iq4_xs.log | tail -12"
echo
echo "===== [3] 新表文件是否存在、行数、表头 ====="
ls -l /home/albus/strata166/data/gfx906-rocblas-5.5.0*.txt
echo "--- 新表头:"; head -1 /home/albus/strata166/data/gfx906-rocblas-5.5.0-6b.txt 2>/dev/null | head -c 120; echo
echo "--- 新表行数:"; grep -c "^f16o" /home/albus/strata166/data/gfx906-rocblas-5.5.0-6b.txt 2>/dev/null
echo
echo "===== [4] 当前配置里的值 ====="
python3 -c "import json;d=json.load(open('/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json'));print('  ', d['env'].get('STRATA_ROCBLAS_TUNING'))"
echo
echo "===== [5] 容器内 /data 能否看到新表 ====="
docker exec strata166-407 bash -lc "ls -l /data/gfx906-rocblas-5.5.0-6b.txt 2>/dev/null || echo '  容器内不存在!'"
