#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render the four-part report's FIRST table to HTML and count its body rows.

GFM spec (verified online 2026-11-07): a table with no body rows emits no
<tbody>; header/delimiter column mismatch means the table is not recognised
at all. This script turns "第一张是空表" into a measurable fact.
"""
import io
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def first_table_lines(path):
    lines = io.open(path, encoding="utf-8").read().splitlines()
    i = next(k for k, l in enumerate(lines) if l.strip().startswith("|"))
    j = i
    while j < len(lines) and lines[j].strip().startswith("|"):
        j += 1
    return lines[i:j]


def ncols(line):
    s = line.strip().replace("\\|", "\x00")
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return len(s.split("|"))


def main():
    for r in ["w1039", "w1040", "w1041", "w1042"]:
        p = os.path.join(ROOT, "albus", r, "reply.md")
        blk = first_table_lines(p)
        cols = [ncols(l) for l in blk]
        print("=== %s first table: %d lines, col counts = %s" % (r, len(blk), cols))
        bad = [(i + 1, n) for i, n in enumerate(cols) if n != cols[0]]
        print("    rows whose column count != header: %s" % (bad or "none"))
        # render just this block
        md = "\n".join(blk) + "\n"
        html = None
        try:
            import markdown
            html = markdown.markdown(md, extensions=["tables"])
        except Exception as e:
            print("    markdown lib unavailable: %s" % e)
        if html is None:
            try:
                from markdown_it import MarkdownIt
                html = MarkdownIt("gfm-like").enable("table").render(md)
            except Exception as e:
                print("    markdown_it unavailable: %s" % e)
        if html is None:
            try:
                import mistune
                html = mistune.create_markdown(plugins=["table"])(md)
            except Exception as e:
                print("    mistune unavailable: %s" % e)
        if html:
            body = re.search(r"<tbody>(.*?)</tbody>", html, re.S)
            nrows = len(re.findall(r"<tr>", body.group(1))) if body else 0
            print("    HTML: <table>=%s  <tbody>=%s  <tr> in tbody=%d"
                  % ("<table>" in html, bool(body), nrows))
            if body:
                trs = re.findall(r"<tr>(.*?)</tr>", body.group(1), re.S)
                for k, tr in enumerate(trs, 1):
                    tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
                    empt = [i + 1 for i, td in enumerate(tds) if not re.sub(r"<[^>]+>", "", td).strip()]
                    if empt:
                        print("    row %2d: %d <td>, EMPTY value cells at %s, text len=%d"
                              % (k, len(tds), empt, len(re.sub(r"<[^>]+>", "", tr))))
                print("    widest cell chars = %d" % max(len(re.sub(r"<[^>]+>", "", tr)) for tr in trs))
        else:
            print("    NO RENDERER AVAILABLE -- structural check only")
    return 0


if __name__ == "__main__":
    sys.exit(main())
