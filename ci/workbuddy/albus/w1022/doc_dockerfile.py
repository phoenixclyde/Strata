#!/usr/bin/env python3
"""Add the build recipe to the Dockerfile that now lives in the repo.

Without it the file is not reproducible: it COPYs two tarballs that are not in git,
and the next person cannot tell where they came from or how the tree hash was fixed.
"""
import io
P = "/home/albus/strata166/pr/strata-fork/ci/docker/Dockerfile-gfx906-0.2.11"
s = io.open(P, encoding="utf-8").read()
head = "# Strata on AMD gfx906"
note = """# How to build this (needs no network; the parent image already has ROCm 7.14-gfx906):
#
#   ctx=/path/to/build-ctx
#   git -C <repo> archive --format=tar.gz -o $ctx/strata-src-0.2.11.tar.gz HEAD
#   cp <llama.cpp pinned tree>.tar.gz $ctx/llama.cpp-3cf0325.tar.gz
#   docker build -t strata-gfx906:0.2.11-101 -f ci/docker/Dockerfile-gfx906-0.2.11 $ctx
#
# The llama.cpp tarball is `git archive` of ggml-org/llama.cpp at
# 3cf03257f219afbe7334045ff7c6a06ac68c627d (tag b11062, 2026-09-20), which is the same
# commit the fork's own CI pins in .github/workflows/metal-build.yml:29.  Its tree hash is
# asserted below, so a swapped tarball fails the build instead of shipping quietly.
"""
if "How to build this" not in s:
    s = s.replace(head, note + "\n" + head, 1)
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("ok", len(s))
