#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W808 扫描器：找出「HIP 分支默认关、非 HIP（CUDA）分支默认开」的开关函数。
   动机：P127 教会我们「宏缺失 => 走到 CUDA 分支」会把 CUDA 的默认带进来（那是被动泄漏）；
        但还有反过来的情形 —— 函数自己写了 `#if defined(STRATA_USE_HIP) ... return false; #else ... default on`，
        于是**我们这类构建主动关掉了 CUDA 上默认开的东西**。这类开关是我们白丢的收益，而且从没被审计过。
   做法：把一个文件里 `bool xxx_on()` 的函数体切出来，看它是否同时含 STRATA_USE_HIP 与 getenv，
        再判断两个分支里 getenv 默认值的三态（nullptr==开 / nullptr==关）。
   输出：env 名 / HIP 默认 / 非HIP 默认 / 源文件:行。
"""
import os, re, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "src"
if not os.path.isdir(ROOT):
    ROOT = os.path.join("deploy/tmp/src022", ROOT)

FN = re.compile(r"^(?:static\s+)?bool\s+(\w+)\s*\(\s*\)\s*\{", re.M)
ENV = re.compile(r'getenv\(\s*"(STRATA_[A-Z0-9_]+)"\s*\)')

rows = []
for dirpath, _, files in os.walk(ROOT):
    for fn in files:
        if not fn.endswith((".cpp", ".cu", ".hpp", ".h")):
            continue
        p = os.path.join(dirpath, fn)
        try:
            s = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        if "STRATA_USE_HIP" not in s:
            continue
        for m in FN.finditer(s):
            start = m.start()
            # 取函数体：从 { 开始按括号配平（最多 4000 字符）
            i = s.index("{", start)
            depth, j = 0, i
            while j < len(s) and j - i < 4000:
                if s[j] == "{":
                    depth += 1
                elif s[j] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            body = s[i:j + 1]
            if "STRATA_USE_HIP" not in body or "getenv" not in body:
                continue
            # 切 HIP 分支与非 HIP 分支
            k = body.find("#if defined(STRATA_USE_HIP)")
            if k < 0:
                k = body.find("#ifdef STRATA_USE_HIP")
            if k < 0:
                continue
            e = body.find("#else", k)
            endif = body.find("#endif", k)
            if e < 0 or endif < e:
                continue
            hip_part, else_part = body[k:e], body[e:endif]
            envs = sorted(set(ENV.findall(body)))
            if not envs:
                continue

            def default_of(part):
                """三态：on（nullptr 也算真）/ off（nullptr 算假）/ unknown"""
                if not ENV.findall(part):
                    return "const:" + ("on" if re.search(r"return\s+true", part) else "off"
                                       if re.search(r"return\s+false", part) else "?")
                # 找 `return v != nullptr` / `return v == nullptr`
                if re.search(r"==\s*nullptr\s*\|\|", part) or re.search(r"==\s*nullptr\s*;", part):
                    return "on(null=on)"
                if re.search(r"!=\s*nullptr", part):
                    return "off(null=off)"
                return "?"
            hip_d, oth_d = default_of(hip_part), default_of(else_part)
            if hip_d != oth_d:
                line = s.count("\n", 0, start) + 1
                rows.append((envs[0], m.group(1), hip_d, oth_d, "%s:%d" % (p.replace("\\", "/"), line)))

print("发现 %d 个「HIP 与非 HIP 默认不同」的开关函数：" % len(rows))
print("%-42s %-28s %-14s %-14s %s" % ("env", "函数", "HIP 默认", "非HIP 默认", "位置"))
for env, fn, hd, od, loc in sorted(rows):
    print("%-42s %-28s %-14s %-14s %s" % (env, fn, hd, od, loc))
