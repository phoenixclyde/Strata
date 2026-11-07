set +e
ls -lt /home/albus/strata166/data/w842_simt2_*.txt 2>/dev/null | head -3
echo "=== 最新输出（尾部） ==="
f=$(ls -t /home/albus/strata166/data/w842_simt2_*.txt 2>/dev/null | head -1)
echo "file=$f"
tail -40 "$f" 2>/dev/null
echo "=== 容器/进程 ==="
docker ps --format '{{.Names}} {{.Status}}' | head -3
pgrep -af "ab_simt2|mt_read|mt_gen" | head -5
