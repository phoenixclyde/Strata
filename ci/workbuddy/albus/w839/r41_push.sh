#!/bin/bash
# W839-41 提交 trace 与文档，推送
set -u
W=/home/albus/strata166/gfx906
cd $W || exit 1
echo "=== status ==="
git status --porcelain
echo "=== diff stat ==="
git diff --stat | tail -3
git add -A src/program/generate.cpp
git -c user.name=phoenixclyde -c user.email=phoenixclyde@users.noreply.github.com \
  commit -q -m "gfx906: print the device probe behind STRATA_W839_TRACE

The entry produced no banner and it was not obvious which of the two cases it was: the call
never ran, or it ran and had nothing to set.  With the probe printed on demand (rc, then the
arch name) that took one run to answer: rc=0, name=gfx906:sramecc+:xnack-, and the table
applied.  Off by default; one getenv per startup when on." || { echo "nothing to commit"; }
git log --oneline -2
echo "=== push ==="
GIT_SSH_COMMAND='ssh -o BatchMode=yes' git push origin gfx906/0.2.8-mi50 2>&1 | tail -3
git rev-parse --short HEAD
