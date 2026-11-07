set +e
L=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
echo "=== 日志里 SIMT=2 的横幅是否有过 ==="
grep -a -c "STRATA_SELECT_SIMT=2), tiles 32/128" "$L"
echo "=== 最近 6 条 qsa select 行 ==="
grep -a "qsa select" "$L" | tail -6
echo
echo "=== 二进制里有没有这段串（确认部署的是含补丁的 n4） ==="
grep -a -c "STRATA_SELECT_SIMT=2), tiles 32/128" /home/albus/strata166/data/bin/strata-0.1.54n4
echo
echo "=== arch_defaults 里 SELECT_SIMT 的设定（会不会覆盖 console env） ==="
grep -n "STRATA_SELECT_SIMT" /home/albus/strata166/src028/src/core/arch_defaults.cpp
echo
echo "=== 容器内的 env 传递：server.py 是否过滤 env ==="
grep -n "def .*env\|STRATA_\" *in\|startswith(\"STRATA_\"" /home/albus/strata166/src028/serve/server.py | head -8
