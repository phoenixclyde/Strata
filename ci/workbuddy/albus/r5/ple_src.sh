#!/bin/bash
# 取 gather / gather_batch 的预取分支（带行号），用于上游 PR 的逐字引用
F=/src/src/kernels/ngram.cpp
docker exec strata166-407 bash -lc "grep -n -e 'g_ple_prefetch' -e 'PrefetchVirtualMemory' -e 'madvise' -e 'void PleTable::gather' -e 'gather_batch' -e 'auto hint' $F"
echo "=== gather() 全文 ==="
docker exec strata166-407 bash -lc "awk '/void PleTable::gather\(/,/^}/' $F | head -50"
