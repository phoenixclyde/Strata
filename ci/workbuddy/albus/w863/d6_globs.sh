#!/bin/bash
B=/home/albus/strata166/gfx029-build
echo "=== VerifyGlobs: what is globbed ==="
head -30 "$B/CMakeFiles/VerifyGlobs.cmake" 2>/dev/null | cut -c1-160
echo "=== did the glob list already contain the .bak files? ==="
grep -c "w862bak\|w863bak" "$B/CMakeFiles/VerifyGlobs.cmake" 2>/dev/null
echo "=== ggml dir in the fork ==="
ls -d /home/albus/strata166/pr/strata-fork/third_party/ggml /home/albus/strata166/pr/strata-fork/llama.cpp 2>/dev/null
ls /home/albus/strata166/pr/strata-fork/third_party/ggml/include/ggml.h 2>/dev/null
echo "=== cache: ggml dir ==="
grep -E "STRATA_GGML_DIR|llama" "$B/CMakeCache.txt" | head -5
echo "=== files in the tree newer than the last configure (07:0x? use CMakeCache mtime) ==="
CFG=$(stat -c %Y "$B/CMakeCache.txt.w863pre" 2>/dev/null || stat -c %Y "$B/CMakeCache.txt")
find /home/albus/strata166/pr/strata-fork -maxdepth 3 -newermt "@$CFG" -type f 2>/dev/null | grep -v "^.*/\.git/" | head -20
