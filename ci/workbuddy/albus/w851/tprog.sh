set +e
f=$(ls -t /home/albus/strata166/data/w851_tune57_*.log 2>/dev/null | head -1)
echo "== $f  $(date +%H:%M:%S)"
echo "--- 已完成 case 数与最新几行:"
grep -ac "^case T=" "$f" 2>/dev/null
grep -aE "^case T=|^best T=|^keep_default|^no_solutions" "$f" 2>/dev/null | tail -8
echo "--- 容器:"
docker ps --format '{{.Names}} {{.Status}}' | grep tune || echo "  (tune 容器不在)"
