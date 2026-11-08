#!/bin/bash
# install the gates as git hooks: code cannot be committed or pushed unless
# the static gate and the round gate both pass.
#
# W1046: this used to assume `.git` is a directory. In a linked worktree
# (`pr/k10` is one, of the `strata-fork` repo) `.git` is a 64-byte FILE, so
# `install ... .git/hooks/pre-commit` died with "Not a directory" -- and because
# it runs with `set -e`, the failure looked like "the hooks were never installed".
# Hooks are shared across worktrees, so they belong in the COMMON dir.
set -e
common=$(git rev-parse --git-common-dir)
[ -d "$common" ] || { echo "not a git repo: $common" >&2; exit 1; }
mkdir -p "$common/hooks"
install -m 755 ci/hooks/pre-commit "$common/hooks/pre-commit"
install -m 755 ci/hooks/pre-push   "$common/hooks/pre-push"
echo "installed $common/hooks/{pre-commit,pre-push} (shared across worktrees)"
