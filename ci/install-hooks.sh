#!/bin/bash
# install the gates as git hooks: code cannot be committed or pushed unless
# the static gate and the round gate both pass.
set -e
cd "$(git rev-parse --show-toplevel)"
install -m 755 ci/hooks/pre-commit .git/hooks/pre-commit
install -m 755 ci/hooks/pre-push   .git/hooks/pre-push
echo "installed .git/hooks/pre-commit + .git/hooks/pre-push"
