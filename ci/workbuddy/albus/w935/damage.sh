#!/bin/bash
set -u
B=~/strata166/gfx029-build

echo "=== A. build.ninja 现状 ==="
ls -l $B/build.ninja* 2>/dev/null | awk '{print "  ", $5, $6, $7, $8, $9}'
echo "  大小: $(stat -c%s $B/build.ninja 2>/dev/null)"
echo "  ngram 引用数: $(grep -c ngram $B/build.ninja 2>/dev/null)"

echo
echo "=== B. 是否有 W921 的备份 ==="
ls -l $B/*.bak* 2>/dev/null | awk '{print "  ", $5, $6, $7, $8, $9}' | head -10

echo
echo "=== C. strata 二进制还在吗（生产用的是容器内 a97f4479，这里只是构建产物） ==="
ls -l $B/strata 2>/dev/null | awk '{print "  ", $5, $6, $7, $8}'
md5sum $B/strata 2>/dev/null

echo
echo "=== D. 生产容器内的引擎（不受影响） ==="
docker exec strata166-407 sh -c "md5sum /data/bin/strata-0.1.55t | cut -c1-32; curl -s -m 3 http://127.0.0.1:8090/health | head -c 40"
