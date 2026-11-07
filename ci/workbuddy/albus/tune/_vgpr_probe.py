#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在 166 上从已构建的引擎二进制里取每个 kernel 的 VGPR / SGPR / 私有段（= 溢出足迹）。
不占 GPU，只读 ELF。用 roc-obj-ls 抽出 code object，再 llvm-readobj --notes 解析 amdhsa 元数据。"""
import subprocess, base64, sys

REMOTE = "albus@192.168.50.166"

SCRIPT = r'''
set -u
IMG=strata-gfx906:0.2.3
docker run --rm --entrypoint sh $IMG -c '
set -u
BIN=/src/build-906/strata
echo "=== bin ==="; ls -l $BIN
cd /tmp && rm -rf hsaco && mkdir hsaco && cd hsaco
roc-obj-ls $BIN 2>/dev/null | head -20
roc-obj-ls -v $BIN 2>/dev/null | grep -oE "/tmp/[^ ]+\.hsaco" | while read f; do
  cp "$f" . 2>/dev/null
done
ls -l *.hsaco 2>/dev/null | head
' 2>&1 | tail -30
'''

def run(b64):
    p = subprocess.run(["ssh", "-o", "BatchMode=yes", REMOTE, "base64 -d | bash"],
                       input=base64.b64encode(b64.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=600)
    return p.stdout.decode("utf-8", "replace")

print(run(SCRIPT))
