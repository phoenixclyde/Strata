#!/bin/bash
echo "=== CMake Error 段 ==="
grep -n -A8 "CMake Error" /home/albus/strata166/data/w859_hblt/cfg_client2.log | head -30
