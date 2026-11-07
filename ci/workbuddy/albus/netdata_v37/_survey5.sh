#!/bin/bash
echo "### TOOLS"; docker exec netdata sh -c 'for x in python3 jq awk sed grep; do printf "%s=%s\n" $x "$(command -v $x || echo NONE)"; done'
echo "### SMART_CT"; docker exec netdata sh -c 'smartctl --version 2>&1 | head -2'
echo "### RECREATE"; sed -n '1,200p' /home/albus/netdata/ops/recreate_netdata.sh
