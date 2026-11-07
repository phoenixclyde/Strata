#!/bin/bash
# W839-18 修正 worktree 的 push 路径（fetch 走代理，push 走 SSH）后推送
set -u
W=/home/albus/strata166/gfx906
cd $W || exit 1
echo "=== 改前 ==="
git remote -v | sed 's#^#  #'
git remote set-url --push origin git@github.com:phoenixclyde/Strata.git
echo "=== 改后 ==="
git remote -v | sed 's#^#  #'
echo "=== push ==="
GIT_SSH_COMMAND='ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new' git push origin gfx906/0.2.8-mi50 2>&1 | tail -5
echo "=== 本地/远端 head ==="
git rev-parse --short HEAD
timeout 40 git ls-remote origin 'refs/heads/gfx906/0.2.8-mi50' 2>&1 | head -2
