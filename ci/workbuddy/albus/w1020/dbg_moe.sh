#!/bin/bash
set -u
cd /out
grep 'moe_mmq.cu.o' _ci_all.txt | grep ' -c ' | head -1 > /tmp/m.sh
bash /tmp/m.sh 2>&1 | grep -E 'error:' | head -8
