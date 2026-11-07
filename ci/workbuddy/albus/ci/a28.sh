#!/usr/bin/env bash
set -eu
cd /home/albus/strata166/pr/strata-fork
python3 ci/gate.py --repo . --source-only 2>&1 | tail -2
git add ci/probe/rs_probe.cpp
git -c user.name=phoenixclyde -c user.email=phoenixclyde@users.noreply.github.com commit -q -F - <<'MSG'
probe: separate the cost of arithmetic from the cost of the LDS round trip

A fifth mode keeps the activation tile in LDS instead of registers -- which is where production
keeps it -- and fills it once per launch so the fill is amortised. Mode 3 (the dummy-register
occupancy arm) is kept but its numbers are not trustworthy: its extra arithmetic is per block, so
it divides a fixed cost by a shrinking amount of work, the same trap that made an earlier probe
report a 4.8x collapse.

HC down, R=1 S=1: read 640 GB/s, arithmetic 535 (-16%), arithmetic via LDS 394 (-26% on top).
At S=16, the LDS arm reads 100 GB/s, which is production's 97. So of the 5.6x gap, roughly 1.2x is
arithmetic and 1.35x is the LDS round trip; what is left points at occupancy (the down kernel
carries 119 VGPR at T=2, i.e. 25%).
MSG
git --no-pager log --oneline -1
timeout 120 git push origin gfx906/mi50 2>&1 | tail -1
git -c user.name=phoenixclyde -c user.email=phoenixclyde@users.noreply.github.com tag -a mi50-0.2.9-r14 -m "MI50 drop r14: rs_probe gains an LDS arm; arithmetic 16% + LDS 26% accounted, remainder points at occupancy. Probe only, engine unchanged." HEAD
timeout 120 git push origin mi50-0.2.9-r14 2>&1 | tail -1
git rev-parse --short HEAD; git describe --exact-match --tags HEAD
