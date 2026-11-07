#!/bin/bash
set -u
F=~/strata166/ci/bench_pair.py

echo "########## A. prompt 生成逻辑 ##########"
grep -n "def make_prompt\|def prompt\|words\|random\|seed\|shuffle" $F | head -20

echo
echo "########## B. prompt 构造的完整函数 ##########"
L=$(grep -n "def make_prompt\|def build_prompt\|def _prompt" $F | head -1 | cut -d: -f1)
if [ -n "${L:-}" ]; then sed -n "${L},$((L+30))p" $F; else echo "(未找到，打印前 60 行)"; sed -n '1,60p' $F; fi

echo
echo "########## C. 是否复用同一个前缀 ##########"
grep -n "PREFILL_TEXT\|BASE_TEXT\|text =\|content" $F | head -14
