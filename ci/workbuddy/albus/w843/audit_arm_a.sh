set +e
echo "=== 18:14-18:23 容器日志（带时间戳）关键行 ==="
docker logs --since 2026-10-31T18:14:00 --until 2026-10-31T18:23:00 -t strata166-407 2>&1 | grep -aE "ready:|still starting|Traceback|Error|error|Restarting|starting the engine" | head -30
echo
echo "=== 该时段内引擎日志的 boot 序列（session is up 行号 + 前后 SIMT 横幅） ==="
L=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
grep -an "session is up\|STRATA_SELECT_SIMT=1), tiles\|STRATA_SELECT_SIMT=2), tiles" "$L" | tail -12
echo
echo "=== n3 在这段有没有跑起来的证据（n3 boot 会打 engine 0.1.54 + 无 SIMT=2） ==="
grep -an "session is up" "$L" | awk -F: '$1>75000 && $1<76800'
