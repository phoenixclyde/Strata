# -*- coding: utf-8 -*-
"""
todo_reconcile.py ---- 待办完整性对账器（防"做做就丢"）

判据：**"出现在计数表里" != "有承载"**。
对每个"源条目"，检查它在 W750 主表里是否有**承载位**（§1 行动项表 / §0.5.5 D 表 /
§0.6-§0.7 登记表 / §2 阶段），只有计数列举而无承载 => 报 GAP。

用法： python todo_reconcile.py            # 打印报告
       python todo_reconcile.py --strict   # 有 GAP 时 exit 1（供收车流程调用）
"""
import io, re, sys

D = 'D:/workbuddy_space/strata_ws/deploy'
W750 = D + '/W750_MASTER_PLAN.md'
REG = D + '/params/PARAM_REGISTER.tsv'
W713 = D + '/W713_PLAN.md'
W749 = D + '/W749_OPT_PLAN.md'


def rd(p):
    return io.open(p, encoding='utf-8', newline='').read()


def sections(s):
    """按 '## ' / '### ' / '#### ' 级别切块，键=标题行原文"""
    out, cur = {}, '__head__'
    out[cur] = []
    for ln in s.split('\n'):
        if re.match(r'^#{2,4} ', ln):
            cur = ln.strip()
            out.setdefault(cur, [])
        out.setdefault(cur, []).append(ln)
    return out


def host_zones(w750):
    """承载区 = 这些节的正文（不含纯计数表）"""
    sec = sections(w750)
    keys = [k for k in sec if re.match(r'^#{2,4} ', k)]
    zones, names = [], []
    for k in keys:
        if re.match(r'^#{2,4} (0\.5\.5|0\.6|0\.6\.1|0\.7|1 |2 )', k) or \
           k.startswith('### 0.5.5') or k.startswith('### 0.6') or \
           k.startswith('### 0.7') or k.startswith('## 1 ') or k.startswith('## 2 '):
            zones.append('\n'.join(sec[k]))
            names.append(k)
    # §1 表在本文件里标题是 '## 1 合并后的行动项（去重，含来源与既有裁定）'
    for k in keys:
        if '合并后的行动项' in k or '阶段与依赖' in k:
            zones.append('\n'.join(sec[k]))
            names.append(k)
    return '\n\n'.join(zones), names


def main():
    w750 = rd(W750)
    reg = rd(REG)
    w713 = rd(W713)
    w749 = rd(W749)

    hz, hz_names = host_zones(w750)

    # ---- 源 1: register CANDIDATE + REFERENCE ----
    src = []
    rows = [l.split('\t') for l in reg.split('\n') if l.strip()]
    hdr = rows[0]
    si = hdr.index('status') if 'status' in hdr else 5
    for f in rows[1:]:
        if len(f) <= si:
            continue
        st = f[si].strip().upper()
        if st in ('CANDIDATE', 'REFERENCE'):
            src.append(('register/' + st, f[0], f[2][:44]))

    # ---- 源 2: W713 §6.4 未关项 ----
    s64 = w713.split('### 6.4')[1].split('\n### ')[0]
    for ln in s64.split('\n'):
        if not ln.startswith('|'):
            continue
        c = [x.strip() for x in ln.strip('|').split('|')]
        if len(c) < 3 or not re.match(r'^\d+$', c[0]):
            continue
        body = c[1]
        if body.startswith('~~'):
            continue                      # 已关
        n = c[0]
        tag = re.findall(r'#\d{3,4}', body)
        src.append(('W713/6.4#' + n, tag[0] if tag else '#' + n, body[:44]))

    # ---- 源 3: W749 C 档 ----
    sc = w749.split('### C 档')[1].split('\n## ')[0]
    for ln in sc.split('\n'):
        if not ln.startswith('|'):
            continue
        c = [x.strip() for x in ln.strip('|').split('|')]
        if len(c) >= 2 and re.match(r'^C\d+$', c[0]):
            src.append(('W749/' + c[0], c[0], c[1][:44]))

    print('=' * 78)
    print('待办对账器  |  源条目 %d  |  W750 承载区 %d 节' % (len(src), len(hz_names)))
    print('=' * 78)

    gaps = []
    for origin, key, desc in src:
        inzone = key in hz
        intable = key in w750
        mark = 'OK ' if inzone else ('CNT' if intable else 'MISS')
        if not inzone:
            gaps.append((origin, key, desc, intable))
        print('%-4s %-16s %-10s %s' % (mark, origin, key, desc))

    print('-' * 78)
    if not gaps:
        print('GAP = 0 ---- 每个源条目都有承载位。')
    else:
        print('GAP = %d ---- 下列条目**只有计数、无承载**（= 会丢）:' % len(gaps))
        for origin, key, desc, intable in gaps:
            print('   [%s] %s  %s   (%s)' % ('CNT' if intable else 'MISS', origin, key, desc))
    print('-' * 78)
    print('承载区节名:', ' | '.join(h[:28] for h in hz_names))
    return 1 if (gaps and '--strict' in sys.argv) else 0


if __name__ == '__main__':
    sys.exit(main())
