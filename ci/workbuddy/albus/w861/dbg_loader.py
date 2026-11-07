#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w861_dbg_loader.py -- 用引擎自己的 CustomYamlLoader 读我们的 block 文件，
逐步回放 parse_mapping 的状态机，定位"k 变成 None 后遇到非 Scalar"的位置。
"""
import sys
import yaml
sys.path.insert(0, "/src/projects/hipblaslt/tensilelite")
from Tensile.CustomYamlLoader import parse_scalar, parse_general  # noqa

path = sys.argv[1]
with open(path, encoding="utf-8") as fh:
    loader = yaml.CSafeLoader(fh)
    loader.get_event()          # StreamStart
    loader.get_event()          # DocumentStart
    # 手工回放顶层
    depth = 0
    n = 0
    trace = []
    while loader.check_event(yaml.DocumentEndEvent) is False:
        ev = loader.peek_event()
        trace.append((n, type(ev).__name__, getattr(ev, "value", ""),
                      ev.start_mark.line + 1))
        n += 1
        if n > 400000:
            break
        loader.get_event()
    print("total events:", n)
    # 找 SequenceStartEvent / ScalarEvent 里 value 为空的
    for idx, kind, val, line in trace:
        if kind == "ScalarEvent" and (val is None or val == "" or val.lower() in ("null", "~")):
            print("EMPTY SCALAR at line %d: %r (%s)" % (line, val, kind))
    # 打印 60..120 区间看结构
    print("--- first 40 events ---")
    for t in trace[:40]:
        print("  #%-6d %-22s %-30r line %d" % t)
