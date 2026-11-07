#!/usr/bin/env bash
# W941: R61 tool-gate -- can rocprofv3 (as launcher, not HSA_TOOLS_LIB injection) collect PMC on gfx906?
set -u
cd /work
rm -rf /tmp/pmcout && mkdir -p /tmp/pmcout
rocprofv3 --pmc VALUBusy --output-format csv -d /tmp/pmcout -- ./stream_roof_w941 32 2 > /tmp/pmc.log 2>&1
echo "RC=$?"
echo "--- log tail ---"
tail -25 /tmp/pmc.log
echo "--- files ---"
find /tmp/pmcout -type f | head -20
echo "--- content ---"
for f in $(find /tmp/pmcout -name '*.csv' | head -3); do echo "== $f"; head -8 "$f"; done
