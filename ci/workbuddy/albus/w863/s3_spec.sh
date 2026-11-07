#!/bin/bash
S=/home/albus/strata166/pr/strata-fork/src/program/generate.cpp
echo "=== --spec / suffix_draft / mtp_max_t wiring ==="
sed -n '3028,3052p' "$S"
echo
echo "=== the draft-chain truncation by spec_min_p ==="
sed -n '13975,14005p' "$S"
echo
echo "=== where max_t_ / max_drafts_ come from ==="
grep -n "max_drafts\|mtp_max_t" "$S" | head -20
