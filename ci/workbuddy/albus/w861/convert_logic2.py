#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w861_convert2.py -- 旧 LibraryLogic -> 新 loader 能吃的格式。

两道坎，都在语法层，不涉及语义：
  1) flow style（`- {K: V}` / `[a, b]`）：loader 的 parse_mapping 只认 block mapping，
     第一个 event 必须是 ScalarEvent；
  2) YAML 锚点/别名（`&id001` / `*id001`）：parse_general 只处理 Mapping/Sequence/Scalar
     三种 event，遇到 AliasEvent 返回 None **且不消费事件** -> 状态机错位，下一次
     parse_scalar 断言必炸。原文件 rocBLAS 那份自带 21 处 ThreadTile 锚点。
     => Dumper.ignore_aliases 返回 True，把别名就地展开。
"""
import sys
import yaml

src, dst = sys.argv[1], sys.argv[2]


class NoAliasDumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True


with open(src, encoding="utf-8") as fh:
    data = yaml.safe_load(fh)

with open(dst, "w", encoding="utf-8") as fh:
    yaml.dump(data, fh, Dumper=NoAliasDumper, default_flow_style=False,
              sort_keys=False, allow_unicode=True, width=4096)

# 自检：重读一遍，确认没有 &id / *id 残留且结构一致
with open(dst, encoding="utf-8") as fh:
    txt = fh.read()
n_anchor = txt.count("&id") + txt.count("*id")
back = yaml.safe_load(txt)
print("anchors left: %d" % n_anchor)
print("structure equal: %s" % (back == data))
print("bytes: %d  lines: %d" % (len(txt), txt.count("\n")))
