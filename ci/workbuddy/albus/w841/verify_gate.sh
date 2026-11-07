set +e
cd /home/albus/strata166/gfx906
echo "=== decode_defaults_arch_ok 定义 ==="
grep -n "decode_defaults_arch_ok" src/program/generate.cpp | head -20
echo "--- 上下文 ---"
sed -n '2120,2175p' src/program/generate.cpp
echo
echo "=== pcie_auto_fork_arch_ok 调用点 ==="
grep -n "pcie_auto_fork_arch_ok" src/program/generate.cpp
echo
echo "=== 日志：PCIe probe / 专家总数 / 策略 ==="
docker exec strata166-407 bash -lc "grep -aiE 'PCIe probe|expert cache [0-9]+ slots|policy is|all experts resident|multi_miss' /data/strata-huihui-ud-iq4_xs.log | tail -8"
echo
echo "=== 日志：启动 args 回显（确认 pcie-frac 走的是显式分支） ==="
docker exec strata166-407 bash -lc "grep -aiE 'pcie_frac=' /data/strata-huihui-ud-iq4_xs.log | tail -3"
