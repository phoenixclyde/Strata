#!/bin/bash
# install the gate as a git hook: code cannot be committed unless the static gate passes.
set -e
cd "$(git rev-parse --show-toplevel)"
install -m 755 ci/hooks/pre-commit .git/hooks/pre-commit
echo "installed .git/hooks/pre-commit"
