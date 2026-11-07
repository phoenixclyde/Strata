set +e
L=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
echo "=== (1) 那 44 条 >5s 的 decode waited 出现在哪 ==="
grep -a -nE 'decode waited [0-9]{4,}\.[0-9]+ ms' $L | head -8 | cut -c1-120
echo "--- 它们附近的引擎启动行（判断日期） ---"
for n in $(grep -a -nE 'decode waited [0-9]{4,}\.[0-9]+ ms' $L | cut -d: -f1 | head -4); do
  d=$(sed -n "1,${n}p" $L | grep -a "engine started" | tail -1 | cut -c1-60)
  echo "  line $n  <- $d"
done
echo
echo "=== (2) 引擎启动次数（每次 = 一个版本/一次重启） ==="
grep -a -c "engine started" $L
grep -a -oE "\[strata\] 2026-[0-9-]+ [0-9:]+ engine started" $L | tail -8
echo
echo "=== (3) 按日统计 prompt 完成行（看基线混了几个版本） ==="
grep -a -B0 -A0 "strata serve: prompt" $L > /tmp/pt.txt
wc -l /tmp/pt.txt
echo "--- 日志行里找日期标记的头 3 条 ---"
grep -a -oE "^[A-Z][0-9]{3,4} [0-9:.]+" $L | head -3
echo
echo "=== (4) 每个版本镜像的标志行 ==="
grep -a -oE "strata-gfx906:[0-9a-z.-]+|version [0-9.]+|v0\.2\.[0-9]+" $L | sort | uniq -c | sort -rn | head -10
