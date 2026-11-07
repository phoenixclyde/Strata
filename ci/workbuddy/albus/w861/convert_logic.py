#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w861_convert_logic.py -- 把 rocBLAS 的旧格式 LibraryLogic（flow style）转成
hipBLASLt TensileLite 的 CustomYamlLoader 能吃的 block style。

判据：报错在 CustomYamlLoader.parse_mapping -> parse_scalar 的 assert，
即"mapping 的 key 位置必须是 ScalarEvent"。旧文件是 `- {K: V}`（FlowMappingStart），
所以只需把 flow 语法摊成 block。不做任何语义翻译。
"""
import sys
import yaml

src, dst = sys.argv[1], sys.argv[2]
with open(src, encoding="utf-8") as fh:
    data = yaml.safe_load(fh)

print("top-level type:", type(data).__name__, "len:", len(data) if hasattr(data, "__len__") else "-")
for i, el in enumerate(data if isinstance(data, list) else []):
    t = type(el).__name__
    n = len(el) if hasattr(el, "__len__") else "-"
    print("  [%d] %-6s len=%s" % (i, t, n))

# block style: 所有 mapping/sequence 都展开成缩进行
with open(dst, "w", encoding="utf-8") as fh:
    yaml.safe_dump(data, fh, default_flow_style=False, sort_keys=False,
                   allow_unicode=True, width=4096)
print("wrote", dst)
