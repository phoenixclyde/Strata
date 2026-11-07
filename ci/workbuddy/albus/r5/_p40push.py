# -*- coding: utf-8 -*-
"""把 ab_p40.sh + 依赖推到 166 并语法检查（不启动）。"""
import sys
sys.path.insert(0, "albus/r5")
from _rsh import sh, push  # noqa: E402

for f in ("ab_p40.sh", "mt_read.py", "mt_gen.py", "lib_a9.sh", "kl_pool.json", "dec_corpus.json"):
    print(push("albus/r5/" + f, "/home/albus/strata166/tmp/" + f), f)
print(sh("cd /home/albus/strata166/tmp && chmod +x ab_p40.sh && bash -n ab_p40.sh && echo SYNTAX_OK && "
         "ls -la kl_pool.json dec_corpus.json mt_read.py mt_gen.py lib_a9.sh", t=90))
