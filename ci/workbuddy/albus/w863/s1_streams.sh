#!/bin/bash
S=/home/albus/strata166/pr/strata-fork/serve
echo "=== knobs that bound concurrency in server.py ==="
grep -nE "MAX_(ACTIVE|CONCURRENT|INFLIGHT|PARALLEL|SLOTS)|max_active|max_concurrent|parallel_slots|SLOT" "$S/server.py" | head -25
echo
echo "=== the queue itself ==="
grep -nE "class .*Queue|def .*queue|pending|admit|waiting" "$S/server.py" | head -30
echo
echo "=== why a second stream waits: search for the admission gate ==="
grep -nE "free_mib|vram_free|headroom|borrow" "$S/server.py" | head -25
