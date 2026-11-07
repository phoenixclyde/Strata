#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w861_probe_pt.py -- 问引擎：ProblemType 的完整字段集是什么。
用一个最小 HHS 描述构造 ProblemType，看它自己填出哪些键，作为补全模板。
"""
import sys

sys.path.insert(0, "/src/projects/hipblaslt/tensilelite")

from Tensile.SolutionStructs.Problem import ProblemType  # noqa: E402

minimal = {
    "OperationType": "GEMM",
    "DataType": "Half",
    "DestDataType": "Half",
    "ComputeDataType": "Float",
    "HighPrecisionAccumulate": True,
    "IndexAssignmentsA": [0, 3, 2],
    "IndexAssignmentsB": [1, 3, 2],
    "NumIndicesC": 3,
    "UseBeta": True,
    "Batched": True,
}
pt = ProblemType(minimal, False)
st = pt.state if hasattr(pt, "state") else dict(pt)
print("n_keys:", len(st))
for k in sorted(st):
    print("  %-40s %r" % (k, st[k]))
