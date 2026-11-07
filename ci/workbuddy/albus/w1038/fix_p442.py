#!/usr/bin/env python3
"""W1038: make P442's restart/停机 wording match report_consistency's parser."""
import io
import importlib.util
import re

P = "deploy/PROGRESS.tsv"
OLD = "（机主 08:30「直接换参数跑了对比」；两次重启，停机 45+45=90 s，config md5 已还原 `5e9b81e2…`）"
NEW = "（机主 08:30「直接换参数跑了对比」；重启 2 次、停机 90 s（45+45），config md5 已还原 `5e9b81e2…`）"


def main():
    s = io.open(P, encoding="utf-8").read()
    if OLD in s:
        s = s.replace(OLD, NEW, 1)
        io.open(P, "w", encoding="utf-8", newline="\n").write(s)
        print("P442 note rewritten")
    elif NEW in s:
        print("already fixed")
    else:
        i = s.find("\tP442\t")
        print("PATTERN MISS; row excerpt:", s[i:i + 700])
        return 1

    spec = importlib.util.spec_from_file_location("rc", "tools/report_consistency.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    print("ledger_numbers(W1038) =", m.ledger_numbers("W1038"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
