#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w861_new_sample.py -- 找 hipBLASLt 自带的新格式 logic 样例，打印 9..12 号元素，
对照旧 rocBLAS 那份缺什么。"""
import glob
import sys
import yaml


def probe(path):
    try:
        d = yaml.safe_load(open(path, encoding="utf-8"))
    except Exception as e:  # noqa
        return None
    if not isinstance(d, list):
        return None
    return d


cands = sys.argv[1:]
shown = 0
for p in cands:
    d = probe(p)
    if d is None:
        continue
    print("=== %s\n    len=%d" % (p.split("/")[-1], len(d)))
    for i in range(9, min(len(d), 13)):
        v = d[i]
        s = repr(v)
        print("    [%d] %-20s %s" % (i, type(v).__name__, s[:160]))
    shown += 1
    if shown >= 4:
        break
