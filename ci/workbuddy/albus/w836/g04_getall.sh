#!/bin/bash
# W836: get upstream main COMPLETELY -- two paths in parallel (git fetch via gh-proxy, and tarball)
F=/home/albus/strata166/pr/strata-fork
cd $F || exit 1
echo "=== A. state ==="
echo "shallow repo? $(git rev-parse --is-shallow-repository 2>&1)"
echo "upstream/main = $(git rev-parse --short upstream/main 2>&1)"
git remote -v | sed 's/^/  /'
echo
echo "=== B. add a gh-proxy mirror remote (idempotent) ==="
git remote remove ghup 2>/dev/null
git remote add ghup https://gh-proxy.com/https://github.com/Niko1221/Strata.git
git remote -v | grep ghup | head -2
echo
echo "=== C. launch two independent fetch paths in background ==="
rm -f /tmp/g_full.log /tmp/g_tar.log /tmp/strata-main.tar.gz
nohup bash -c 'cd /home/albus/strata166/pr/strata-fork && git fetch ghup main --no-tags > /tmp/g_full.log 2>&1; echo "RC=$?" >> /tmp/g_full.log' >/dev/null 2>&1 &
echo "  [1] git fetch ghup main  (full history) -> /tmp/g_full.log"
nohup bash -c 'curl -L --retry 3 --max-time 1500 -o /tmp/strata-main.tar.gz \
  https://gh-proxy.com/https://github.com/Niko1221/Strata/archive/refs/heads/main.tar.gz > /tmp/g_tar.log 2>&1; \
  echo "RC=$?" >> /tmp/g_tar.log' >/dev/null 2>&1 &
echo "  [2] tarball of main -> /tmp/strata-main.tar.gz"
echo
sleep 20
echo "=== D. early progress ==="
echo "--- fetch log ---"; tail -3 /tmp/g_full.log 2>/dev/null || echo "(empty)"
echo "--- tarball ---"; ls -la /tmp/strata-main.tar.gz 2>/dev/null || echo "(not yet)"
