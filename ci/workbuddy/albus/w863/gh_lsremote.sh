#!/bin/bash
cd /home/albus/strata166/pr/strata-fork || exit 1
echo "=== origin (phoenixclyde) heads ==="
git ls-remote --heads origin 2>&1 | awk '{print substr($1,1,8), $2}' | sed 's#refs/heads/##' | sort -k2
echo
echo "=== upstream (Niko1221) heads ==="
git ls-remote --heads upstream 2>&1 | awk '{print substr($1,1,8), $2}' | sed 's#refs/heads/##' | sort -k2
echo
echo "=== local HEAD ==="
git rev-parse --short HEAD; git rev-parse --abbrev-ref HEAD
