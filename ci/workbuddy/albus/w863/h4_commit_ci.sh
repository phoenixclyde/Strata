#!/bin/bash
# [W863] Commit the CI fix on the downstream trunk and push it.  Keeps .bak files out of the tree.
set -eu
cd /home/albus/strata166/pr/strata-fork

mkdir -p /home/albus/strata166/w863/kernel_bak
[ -f serve/telemetry.py.w863bak ] && mv -f serve/telemetry.py.w863bak /home/albus/strata166/w863/kernel_bak/telemetry.py.w863bak

echo "=== untracked before ==="
git status --porcelain --untracked-files=all | head -10

git add serve/telemetry.py
git -c user.name=phoenixclyde -c user.email=phoenixclyde@users.noreply.github.com \
  commit -q -m @'serve/telemetry: keep the sampler thread references (fixes CI red on gfx906/*)

Our PCIe-bandwidth patch replaced
    self._thread = threading.Thread(...); self._thread.start()
with an anonymous thread.  Upstream v0.2.9 added
serve/test_responses.NoLeakedSampler, which reads `telemetry._thread` to prove a
stopped server ends its sampler -- the attribute was None, so
"Minimal serving runtime" failed on every gfx906/* push while main stayed green.

close() now joins both sampler threads (the 1 Hz sampler and the 5 s PCIe reader).

Counter-proof, same tree, only this file swapped:
  .w863bak (anonymous thread) -> FAIL "the server did not start its hardware sampler thread"
  this commit                 -> OK
'@

echo "=== head ==="
git --no-pager log --oneline -1
echo "=== tree clean? ==="
git status --porcelain --untracked-files=all | wc -l
echo "=== push ==="
timeout 120 git push origin gfx906/mi50 2>&1 | tail -3
