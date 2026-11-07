#!/usr/bin/env bash
# Commit the real multi-turn probe and withdraw the upstream claim.
set -eu
R=/home/albus/strata166/pr/strata-fork
cd "$R"

echo "=== gate ==="
python3 ci/gate.py --repo . --source-only 2>&1 | tail -2

echo
echo "=== commit ==="
git add ci/prefill_multiturn.py
git -c user.name=phoenixclyde -c user.email=phoenixclyde@users.noreply.github.com commit -q -F - <<'MSG'
probe: real multi-turn shape -- the engine already reuses 80% of the prefix

The previous probe built turn 2 as "turn 1 plus new words", skipping the model's own reply. A
real second turn is [user P1][assistant reply1][user P2], and a parked conversation holds exactly
P1+reply1. Without the reply the prompts diverge at the first new token, so the earlier "0 reused"
was the right answer to the wrong question -- and I nearly reported it upstream as a missing
feature. It is not missing: conversation_prefix() is a prefix test, ConversationCache::best()
takes the longest prefix, borrows()/take() decide borrow versus take.

Measured on the live service, n=3, turn 2 against a single prompt of the same total length:

  turn2   2214 / 2207 / 2044 ms      single   4351 / 4306 / 4231 ms      ratio 51 / 51 / 48 %

log, verbatim:

  prompt 2336 tokens = 1867 reused + 469 read in 1586 ms (295.7 tok/s), 2 checkpoints
  prompt 2333 tokens =    0 reused + 2333 read in 3750 ms (622.1 tok/s), 1 checkpoints

80% reused, TTFT 2.4x. What is left is not the match, it is the restore: 469 tokens are worth
about 754 ms at the control's rate, but the turn took 1586 ms, so roughly 830 ms goes to
restoring the parked K/V and mounting its checkpoint -- 260 MB of snapshot in 0.8 s, about
300 MB/s, far below what PCIe can do. That is the next target, not the matching.

Withdraws candidate C4 in deploy/UPSTREAM_CONTRIB.md and entry R41 in the progress ledger.
MSG
git --no-pager log --oneline -1

echo
echo "=== push + tag ==="
timeout 120 git push origin gfx906/mi50 2>&1 | tail -1
git -c user.name=phoenixclyde -c user.email=phoenixclyde@users.noreply.github.com tag -a mi50-0.2.9-r13 \
  -m "MI50 drop r13: real multi-turn probe; measured 80% prefix reuse (TTFT 2.4x) and located the remaining ~830 ms in the parked-K/V restore. Withdraws the upstream C4 claim. Engine unchanged." HEAD
timeout 120 git push origin mi50-0.2.9-r13 2>&1 | tail -1

echo
echo "=== final ==="
git rev-parse --short HEAD
git describe --exact-match --tags HEAD
git status --porcelain --untracked-files=all | wc -l
