#!/bin/bash
set -u
cd /out
L=$(grep 'moe_mmq.cu.o' _ci_all.txt | grep ' -c ' | head -1)
echo "cmd_len=${#L}"
bash -c "$L" > /tmp/mo.log 2>&1
echo "rc=$?"
grep -E 'error:' /tmp/mo.log | head -8
