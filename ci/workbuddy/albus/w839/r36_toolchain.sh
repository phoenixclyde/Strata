#!/bin/bash
# W839-36 查参数改动工具链（记忆里说改参唯一道 = register -> gen_config --write）
S=/home/albus/strata166/src028
echo "=== gen_config 是否存在 ==="
ls -la $S/tools/gen_config.py 2>/dev/null || echo "no gen_config.py in src028/tools"
find /home/albus/strata166 -maxdepth 3 -name 'gen_config*' -o -maxdepth 3 -name '*param*register*' 2>/dev/null | head -8
echo
echo "=== 生产配置是怎么来的（看有没有生成器痕迹）==="
head -6 /home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
echo
echo "=== 现有配置备份 ==="
ls -la /home/albus/strata166/data/*.json | head -8
echo
echo "=== 现在生产/门禁状态 ==="
docker ps --format '{{.Names}} {{.Status}}' | grep strata166 || echo PROD_DOWN
tail -3 /home/albus/strata166/data/w839_b2.out
