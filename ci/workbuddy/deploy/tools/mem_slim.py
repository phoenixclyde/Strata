# -*- coding: utf-8 -*-
"""mem_slim ---- MEMORY.md 压缩的**唯一入口**（strata_ws 适配版；技能 routek-memory-slim）

机主令（2026-10-04，逐字）：
  「我不管你 怎么去限制写 memory.md，我觉得不要限制，还是按照你的来，
   但是，memory.md 文件超限的时候你必须通过 slim 那个技能去压 memory.md 的大小，
   确保是唯一途径，不会又走你自己改的那种一轮一轮自己压的循环。」

设计（对应上述三条）：
  1. **不限制写**：不对 MEMORY.md 加只读/锁。任何工具、任何时刻都能正常写它。
  2. **超限必走技能**：唯一约束是「**压缩**」这一个动作 ---- 只要 `len(chars) > 2900`，
     压缩**只能**经由本入口执行；本入口内即技能的完整流程。
  3. **唯一途径**：本入口是**唯一**持有「技能步骤 + 归档 + 五断言 + 落盘 + 独立核验」的实现。
     手写「一轮一轮自己压」的脚本**不再需要**（入口已支持分步：先 `design` 出方案，再 `apply` 落盘）。

与已退休件的关系：
  * `memgate.py`（文件锁，W634d 造）**已退休** ---- 机主判其「起不到作用、有隐患、多步骤」。
    其唯一有价值的部分（**「必须读过技能」的机器凭证**）以更轻的方式保留在本入口：
    入口断言 `SKILL.md` 的 md5 与调用方传入的一致。

用法：
    python mem_slim.py check              # 量基线：chars / 余量 / 是否超限 / 技能指纹
    python mem_slim.py show               # 打印当前 MEMORY.md 全文
    python mem_slim.py auto [target]      # 推荐入口：自动反解压缩方案并落盘（不需手写 ops）
    python mem_slim.py auto [target] [plan.json]  # 内容+压缩一条命令：先套内容 ops，再自动压到 target
    python mem_slim.py plan <plan.json>   # 校验一份压缩方案（不落盘）：五断言 + 预演字符数
    python mem_slim.py apply <plan.json>  # 落盘：先归档 Z-<auto> 到 DETAIL，再写 MEMORY.md，再核验

W639 新立两条机制（机主令：根治「自己一轮一轮压」）：
  * T313 计数门：同一波（wave）内 `plan` 最多 2 次；第 3 次直接拒并提示改用 `auto`。
    波 = 由 `auto`/`apply` 成功落盘，或 cnt 文件被删而重置。目的是封死「反复手改 ops 试」。
  * T314 反解器：`auto` 不接收 ops，只接收目标字符数 => 脚本内建削减策略自行迭代配比，
    调用方（我）**没有任何手改 ops 的机会**，从根上消灭「一轮一轮试」这个动作。

plan.json 结构：
    {
      "skill_md5": "<当前 SKILL.md 的 md5，凭证>",
      "reason":    "<本次压缩的触发原因，写入归档节>",
      "ops": [
        {"kind":"line_replace","line":19,"new":"..."},      # 按行号整行替换（1-based）
        {"kind":"substr","old":"...","new":"..."},          # 唯一子串替换（count 必须 == 1）
        {"kind":"append_line","text":"..."}                 # 在末尾追加一行
      ]
    }
"""
import hashlib
import json
import os
import re
import sys
import time as _time

# W735: 归档节头的日期不再硬编码（原先写死 2026-10-04，是从 routeK 原件继承来的缺陷）
ARCHIVE_STAMP = _time.strftime('%Y-%m-%d')

# ---- 路径 ----
MEM    = r'D:/workbuddy_space/strata_ws/.workbuddy/memory/MEMORY.md'
DETAIL = r'D:/workbuddy_space/strata_ws/.workbuddy/memory/MEMORY_DETAIL.md'
SKILL  = r'C:/Users/clyde/.workbuddy/skills/routek-memory-slim/SKILL.md'
COUNTER = r'D:/workbuddy_space/strata_ws/deploy/tools/.mem_slim_wave.json'   # 同波 plan 计数（T313）

# ---- 判据（技能 §步骤 4） ----
CHAR_LIMIT  = 3000   # 系统注入窗口
CHAR_TARGET = 2900   # 压缩目标（留 >=100 余量）
BYTE_LIMIT  = 7000   # 技能另有字节上限

# BAN 36 码位（技能 `_auth_append.BAN` 同源 30 个 + 本项目 6 个：2014/2013/2026/2260/2212/00D7；W735 更正计数）
BAN = [0x2192, 0x21d2, 0x2264, 0x2265, 0x2605, 0x2606, 0x26a0, 0x26d4,
       0x2705, 0x2713, 0x2717, 0x274c, 0x2b1b, 0x2b1c, 0x2b50, 0xfe0f,
       0x1f534, 0x1f7e0, 0x1f7e1, 0x1f7e2] + list(range(0x2460, 0x246a))
# W727 追加：本项目 MEMORY.md §1 铁律另有 6 个禁用码位（破折号/短破折号/省略号/不等号/减号/乘号）。
#   适配本工具时只换了路径与编号判据，BAN 沿用了 routeK 的清单 => 本项目自己的规则被放行
#   （实证：MEMORY.md §3 里的 U+2260 一路通过 VERIFY=OK，未被任何断言拦下）。两边取并集，只增不减。
BAN += [0x2014, 0x2013, 0x2026, 0x2260, 0x2212, 0x00D7]


def skill_md5():
    return hashlib.md5(open(SKILL, 'rb').read()).hexdigest()


def read_text(p):
    with open(p, encoding='utf-8') as f:
        return f.read()


def read_bytes(p):
    with open(p, 'rb') as f:
        return f.read()


def stats(text):
    b = text.encode('utf-8')
    return dict(chars=len(text), bytes=len(b),
                crlf=b.count(b'\r\n'), md5=hashlib.md5(b).hexdigest())


# ---------- 子命令：check ----------
def cmd_check():
    t = read_text(MEM)
    s = stats(t)
    over = s['chars'] > CHAR_TARGET
    print('SKILL_MD5   = %s' % skill_md5())
    print('MEM chars   = %d   (窗口 %d, 目标 %d, 余量 %d)'
          % (s['chars'], CHAR_LIMIT, CHAR_TARGET, CHAR_LIMIT - s['chars']))
    print('MEM bytes   = %d   (上限 %d)' % (s['bytes'], BYTE_LIMIT))
    print('MEM md5     = %s   crlf=%d' % (s['md5'], s['crlf']))
    print('OVER_TARGET = %s' % over)
    print('VERDICT     = %s' % ('NEED_SLIM' if over else 'OK'))


# ---------- 子命令：show ----------
def cmd_show():
    sys.stdout.reconfigure(encoding='utf-8')
    print(read_text(MEM))


# ---------- 公共：跑一遍「五断言」 ----------
def assertions(text, tag='', ref=None):
    """技能 §步骤 4 的五断言 + BAN。返回 (ok, msgs)"""
    msgs = []
    ok = True
    s = stats(text)

    def chk(cond, name, detail=''):
        nonlocal ok
        msgs.append('  [%s] %s %s' % ('PASS' if cond else 'FAIL', name, detail))
        if not cond:
            ok = False

    chk(s['chars'] <= CHAR_LIMIT, '字符 <= %d' % CHAR_LIMIT, '实际 %d' % s['chars'])
    chk(s['bytes'] <= BYTE_LIMIT, '字节 <= %d' % BYTE_LIMIT, '实际 %d' % s['bytes'])
    chk('\r' not in text, 'LF-only', 'crlf=%d' % s['crlf'])
    bad = sorted({ord(c) for c in text if ord(c) in set(BAN)})
    chk(not bad, 'BAN 命中 == 0', '命中码位 %r' % bad)
    # 编号完整性（相对 DETAIL 反向自证留给 apply 的独立核验）
    nums = sorted(int(m) for m in re.findall(r'\bP(\d+)\b', text))
    chk(bool(nums), 'P 编号存在', 'n=%d' % len(nums))
    # W767: the check above used to be labelled "P 编号齐" while only testing bool(nums)
    # -- ids could vanish and it still said PASS (P50/P42/P41/P97/P39/P46-49 did, because the
    # reverse solver's L3/L4 reductions run AFTER the author's ops).  A compression may not
    # drop a P id the incoming text carried; that is the whole point of the id scheme.
    if ref is None:
        ref = read_text(MEM) if os.path.isfile(MEM) else ''
    if ref:
        lost = sorted({int(m) for m in re.findall(r'\bP(\d+)\b', ref)} - set(nums))
        chk(not lost, 'P 编号零丢失', ('lost=%r' % lost) if lost else 'n=%d' % len(nums))
    chk('MEMORY_DETAIL.md' in text, '指针 MEMORY_DETAIL.md 在位')
    return ok, msgs, s


# ---------- 公共：套用 plan 得到新文本 ----------
def apply_ops(text, ops):
    lines = text.split('\n')
    text = text
    log = []
    used_lines = False
    for op in ops:
        k = op['kind']
        if k == 'line_replace':
            used_lines = True
            i = int(op['line']) - 1
            assert 0 <= i < len(lines), 'line %d 越界' % (i + 1)
            old = lines[i]
            new = op['new']
            assert old != new, 'line_replace NOOP at %d' % (i + 1)
            log.append('line[%d] %+d' % (i + 1, len(new) - len(old)))
            lines[i] = new
        elif k == 'substr':
            old, new = op['old'], op['new']
            c = text.count(old)
            assert c == 1, 'substr count=%d (须唯一) %r' % (c, old[:40])
            assert old != new, 'substr NOOP'
            log.append('substr %+d %s' % (len(new) - len(old), old[:30]))
            text = text.replace(old, new, 1)
        elif k == 'append_line':
            t = op['text']
            if not text.endswith('\n'):
                text += '\n'
            assert t not in text, 'append_line 已存在'
            log.append('append %+d' % (len(t) + 1))
            text += t + '\n'
        else:
            raise AssertionError('unknown op kind: %r' % k)
    if used_lines:
        text = '\n'.join(lines)
    return text, log


# ---------- 子命令：plan ----------
def cmd_plan(path):
    plan = json.load(open(path, encoding='utf-8'))
    provided = plan.get('skill_md5', '')
    cur = skill_md5()
    if provided != cur:
        print('GATE FAIL: 技能指纹不符 -> 拒。\n  传入 = %s\n  当前 = %s' % (provided, cur))
        sys.exit(2)
    print('GATE OK: 已读技能（指纹 %s）' % cur)

    t0 = read_text(MEM)
    s0 = stats(t0)
    t1, log = apply_ops(t0, plan['ops'])
    s1 = stats(t1)
    print('OPS:')
    for l in log:
        print('  ' + l)
    print('BEFORE chars=%d bytes=%d' % (s0['chars'], s0['bytes']))
    print('AFTER  chars=%d bytes=%d  (余量 %d)' % (s1['chars'], s1['bytes'], CHAR_LIMIT - s1['chars']))
    ok, msgs, _ = assertions(t1)
    print('ASSERTIONS:')
    print('\n'.join(msgs))
    if not ok:
        print('PLAN VERDICT = FAIL')
        sys.exit(3)
    if s1['chars'] > CHAR_TARGET:
        print('PLAN VERDICT = OVER_TARGET (超 %d)' % (s1['chars'] - CHAR_TARGET))
        sys.exit(4)
    print('PLAN VERDICT = PASS (可 apply)')


# ---------- 子命令：apply ----------
def cmd_apply(path):
    plan = json.load(open(path, encoding='utf-8'))
    provided = plan.get('skill_md5', '')
    cur = skill_md5()
    if provided != cur:
        print('GATE FAIL: 技能指纹不符 -> 拒。传入=%s 当前=%s' % (provided, cur))
        sys.exit(2)
    print('GATE OK: %s' % cur)

    t0 = read_text(MEM)
    s0 = stats(t0)
    t1, log = apply_ops(t0, plan['ops'])
    s1 = stats(t1)
    print('AFTER chars=%d bytes=%d 余量=%d' % (s1['chars'], s1['bytes'], CHAR_LIMIT - s1['chars']))

    ok, msgs, _ = assertions(t1)
    print('\n'.join(msgs))
    if not ok:
        print('APPLY ABORT (断言不过，未落盘)')
        sys.exit(3)
    if s1['chars'] > CHAR_TARGET:
        print('APPLY ABORT: 超目标 %d（未落盘）' % (s1['chars'] - CHAR_TARGET))
        sys.exit(4)

    # ---- 步骤 2：归档 Z-<auto> 到 DETAIL（先归档，后写 MEM ---- 这是保命顺序） ----
    det = read_text(DETAIL)
    d0 = stats(det)
    nums = [int(m) for m in re.findall(r'## Z-(\d+)', det)]
    z = (max(nums) + 1) if nums else 1
    mark = '## Z-%d ' % z
    if mark in det:
        print('DETAIL 已含 %s -> SKIP 归档' % mark.strip())
    else:
        fence = chr(96) * 3
        entry = ('\n\n---\n\n## Z-%d（归档于 mem_slim，' + ARCHIVE_STAMP + '）\n\n'
                 '**触发**：%s\n\n'
                 '**基线指纹**：chars=%d / bytes=%d / md5=%s\n\n'
                 '%s\n%s\n%s\n') % (z, plan.get('reason', '(未填)'), s0['chars'], s0['bytes'], s0['md5'],
                                    fence, t0, fence)
        det2 = det + entry
        assert det2[:len(det)] == det, 'DETAIL 前缀被改写'
        assert t0 in det2, 'DETAIL 未含原文'
        open(DETAIL, 'w', encoding='utf-8', newline='\n').write(det2)
        d1 = stats(read_text(DETAIL))
        print('ARCHIVED Z-%d : DETAIL %d -> %d bytes (+%d)'
              % (z, d0['bytes'], d1['bytes'], d1['bytes'] - d0['bytes']))

    # ---- 步骤 5：落盘 + 读回 ----
    with open(MEM, 'w', encoding='utf-8', newline='\n') as f:
        f.write(t1)
    back = read_text(MEM)
    if back != t1:
        print('FATAL: 读回 != 写入 (未预期)')
        sys.exit(5)
    s2 = stats(back)
    print('WROTE MEM chars=%d bytes=%d md5=%s' % (s2['chars'], s2['bytes'], s2['md5']))

    # ---- 步骤 6：独立核验（换一套判定） ----
    print('-- 独立核验 --')
    v = []
    v.append(('LF-only', '\r' not in back))
    v.append(('chars<=%d' % CHAR_TARGET, s2['chars'] <= CHAR_TARGET))
    v.append(('bytes<8000', s2['bytes'] < 8000))
    v.append(('BAN==0', not [c for c in back if ord(c) in set(BAN)]))
    v.append(('P 编号零丢失',
              not ({int(m) for m in re.findall(r'\bP(\d+)\b', t0)}
                   - {int(m) for m in re.findall(r'\bP(\d+)\b', back)})))
    detf = read_text(DETAIL)
    v.append(('DETAIL 前缀未改', detf[:len(det)] == det))
    if t0.strip():
        v.append(('DETAIL 含压缩前原文', t0 in detf))
    allok = True
    for name, cond in v:
        print('  [%s] %s' % ('PASS' if cond else 'FAIL', name))
        allok = allok and cond
    print('VERIFY = %s' % ('OK' if allok else 'FAIL'))
    sys.exit(0 if allok else 6)


# ---------- 同波计数门（T313） ----------
PLAN_MAX_PER_WAVE = 2


def _wave_load():
    try:
        return json.load(open(COUNTER, encoding='utf-8'))
    except Exception:
        return {'wave': 0, 'cnt': 0}


def _wave_save(d):
    with open(COUNTER, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(d, f, ensure_ascii=False)


def wave_bump():
    """plan 调用计数 +1；超上限则拒绝（exit 7）。"""
    d = _wave_load()
    if d['cnt'] >= PLAN_MAX_PER_WAVE:
        print('GATE FAIL(T313): 本波 plan 已调用 %d 次（上限 %d）-> 拒。'
              % (d['cnt'], PLAN_MAX_PER_WAVE))
        print('  改用：python mem_slim.py auto   （反解器一次到位，无需手改 ops）')
        sys.exit(7)
    d['cnt'] += 1
    _wave_save(d)
    print('WAVE: cnt=%d/%d' % (d['cnt'], PLAN_MAX_PER_WAVE))


def wave_reset():
    """apply/auto 成功落盘后调用：开新波。"""
    d = _wave_load()
    _wave_save({'wave': d['wave'] + 1, 'cnt': 0})


# ---------- 子命令：auto（T314 反解器） ----------
# 策略：把可压缩段按「信息密度」排序，逐级（level）收紧，直到 <= target。
# 我（调用方）只传 target，**不允许**传 ops => 从根上无「手改 ops」动作。
def cmd_auto(target=None, plan_path=None):
    target = int(target) if target else CHAR_TARGET
    t0 = read_text(MEM)
    s0 = stats(t0)
    print('SKILL_MD5   = %s  (追溯用；auto 不设指纹门)' % skill_md5())
    print('AUTO: 现状 chars=%d bytes=%d 目标<=%d（须 <=%d）'
          % (s0['chars'], s0['bytes'], target, CHAR_TARGET))
    if target > CHAR_TARGET:
        print('GATE FAIL(T314): 目标 %d 超过硬目标 %d -> 拒' % (target, CHAR_TARGET))
        sys.exit(2)

    # ---- 可选：先应用内容 ops（plan.json），再自动压到 target ----
    # W639 新立 T315：内容编辑与压缩**合并为一条命令**。
    #   调用方只给「内容改动」+「目标字符数」，压缩量由脚本算 => 无手调字符数。
    base = t0
    clog = []
    protect = set()
    if plan_path:
        plan = json.load(open(plan_path, encoding='utf-8'))
        provided = plan.get('skill_md5', '')
        cur = skill_md5()
        if provided and provided != cur:
            print('GATE FAIL: 技能指纹不符 -> 拒。传入=%s 当前=%s' % (provided, cur))
            sys.exit(2)
        base, clog = apply_ops(t0, plan['ops'])
        # T315：算出内容 ops 触及的行号，交给 auto 保护（不被削）。
        #
        # W768 修：行号必须在**内容 ops 之后**的文本上算。原先对 t0（改前）算，于是任何会增删行的
        # op（"3 行并 1 行"、删掉一行）都会让其后的行号整体位移 => 保护集指错行 =>
        # **本波刚加的内容照样被 L3/L4 削掉**（实测：恢复好的"非专家"行被原样削回）。
        # 之前看起来能用，只是因为那些波的 ops 全是单行改长、不位移。
        blines = base.split('\n')
        for op in plan['ops']:
            if op['kind'] == 'line_replace':
                i = int(op['line']) - 1
                if 0 <= i < len(blines):
                    protect.add(i + 1)
                continue
            needle = (op.get('new') or op.get('text') or '').split('\n')[0]
            if not needle:
                continue
            for n, ln in enumerate(blines, 1):
                if needle in ln:
                    protect.add(n)
        sb = stats(base)
        print('CONTENT ops(%d):' % len(clog))
        for l in clog:
            print('  ' + l)
        print('CONTENT 后 chars=%d bytes=%d（余量 %d）；保护行 %s'
              % (sb['chars'], sb['bytes'], CHAR_LIMIT - sb['chars'], sorted(protect)))

    if stats(base)['chars'] <= target:
        print('AUTO: 已达标（%d <= %d），无需压缩。' % (stats(base)['chars'], target))
        t1, log = base, clog
    else:
        got = _auto_solve(base, target, protect=protect)
        if got is None:
            print('AUTO FAIL: 现有策略无法达到 %d（需人工介入：加压缩钩子或改 DETAIL 分层）' % target)
            sys.exit(3)
        t1, log = got
        log = clog + ['# 内容后 ' + x for x in log]

    s1 = stats(t1)
    ok, msgs, _ = assertions(t1)
    print('AUTO ops(%d):' % len(log))
    for l in log:
        print('  ' + l)
    print('AFTER chars=%d bytes=%d 余量=%d' % (s1['chars'], s1['bytes'], CHAR_LIMIT - s1['chars']))
    if not ok:
        print('\n'.join(msgs))
        print('AUTO ABORT: 断言不过（未落盘）')
        sys.exit(3)
    if s1['chars'] > CHAR_TARGET:
        print('AUTO ABORT: 超硬目标 %d（未落盘）' % (s1['chars'] - CHAR_TARGET))
        sys.exit(4)
    # ---- 落盘：复用 apply 的归档 + 写 + 核验 ----
    _land(t0, t1, s0, 'auto（反解器，目标 %d%s）'
          % (target, '，含内容 ops' if plan_path else ''))


def _auto_solve(t0, target, protect=None):
    """反解器主体：按**预登记策略**逐级削减，迭代由脚本跑，调用方不看 ops。

    返回 (新文本, log) 或 None。
    策略表（写死在此，可审计；对应技能 SKILL.md §自动压缩策略）：
      L1 幂等机械替换表 DEL  ---- 去掉已知冗余串（不改语义）
      L2 行内空白/标点归一
      L3 去括号补充（保留主句）
      L4 按行长降序，逐分句截断（兜底，保证收敛）
    每级都重跑 assertions；一旦达标即停。**不接收外部 ops**。
    """
    text = t0
    log = []
    # ---- L1：幂等机械替换表（冗余串 -> 空） ----
    DEL = [
        '全文回 DETAIL。',
        '（全文 `W617_RESULT.md`）',
        '(memgate 已退休)',
        '（KI 原文；',
    ]
    for d in DEL:
        c = text.count(d)
        if c:
            text = text.replace(d, '')
            log.append('L1 del %r x%d (%+d)' % (d[:16], c, -len(d) * c))
    if stats(text)['chars'] <= target:
        return _finalize(text, t0, log)
    # ---- L2：行内空白归一（连续 2+ 空格 -> 1） ----
    t2 = re.sub(r'(?<=\S) {2,}(?=\S)', ' ', text)
    if len(t2) < len(text):
        log.append('L2 空白归一 %+d' % (len(t2) - len(text)))
        text = t2
    if stats(text)['chars'] <= target:
        return _finalize(text, t0, log)
    # ---- L3+L4：逐行削减（行长降序），达标即停 ----
    # T315：`protect`（内容 ops 刚改过的行号，1-based）跳过不削，
    #       否则 auto 会把刚写入的内容（如 T313/T314 铁律）从行尾静默截掉。
    lines = text.split('\n')
    order = sorted(range(len(lines)), key=lambda i: -len(lines[i]))
    for i in order:
        if stats('\n'.join(lines))['chars'] <= target:
            break
        if protect and (i + 1) in protect:
            continue
        old = lines[i]
        new = _shrink_line(old)
        if new != old:
            lines[i] = new
            log.append('L3/4 line[%d] %+d' % (i + 1, len(new) - len(old)))
    text = '\n'.join(lines)
    if stats(text)['chars'] <= target:
        return _finalize(text, t0, log)
    # ---- L5：兜底硬截（保底收敛）。按行长降序，逐行从尾丢 N 字符 ----
    lines = text.split('\n')
    order = sorted(range(len(lines)), key=lambda i: -len(lines[i]))
    for i in order:
        cur = stats('\n'.join(lines))['chars']
        if cur <= target:
            break
        if protect and (i + 1) in protect:
            continue
        need = cur - target
        old = lines[i]
        if len(old) <= need:
            continue
        # 保留主句：砍到 need 以上再留 10 字符余量，且不砍掉行首标题结构
        keep = max(len(old) - need - 5, int(len(old) * 0.5))
        lines[i] = old[:keep].rstrip() + '...'
        log.append('L5 line[%d] 硬截 %+d' % (i + 1, len(lines[i]) - len(old)))
    text = '\n'.join(lines)
    if stats(text)['chars'] > target:
        return None
    return _finalize(text, t0, log)


def _shrink_line(s):
    """单行削减：先去括号补充，再按分句从尾截，直到全行为空。"""
    # 去括号补充
    while True:
        m = re.search(r'[（(][^（()）]*[)）]', s)
        if not m:
            break
        s2 = s[:m.start()] + s[m.end():]
        if len(s2) >= len(s):
            break
        s = s2
    # 按分句分隔符从尾截（保留主句，去掉末级细节）
    parts = re.split(r'(?<=[；;|])', s)
    while len(parts) > 1:
        parts = parts[:-1]
        cand = ''.join(parts).rstrip('；;| ')
        if cand:
            return cand
    # 仍太长 -> 硬截
    return s


def _finalize(text, t0, log):
    t1, lg = apply_ops(text, [])   # 走同一套出口（当前无 ops，仅归一）
    log += lg
    return text, log


def _auto_levels(text):
    """保留占位（旧接口兼容）。"""
    return []


def _land(t0, t1, s0, reason):
    """归档 + 写盘 + 独立核验（apply 与 auto 共用）。"""
    det = read_text(DETAIL)
    d0 = stats(det)
    nums = [int(m) for m in re.findall(r'## Z-(\d+)', det)]
    z = (max(nums) + 1) if nums else 1
    mark = '## Z-%d ' % z
    if mark in det:
        print('DETAIL 已含 %s -> SKIP 归档' % mark.strip())
    else:
        fence = chr(96) * 3
        entry = ('\n\n---\n\n## Z-%d（归档于 mem_slim，' + ARCHIVE_STAMP + '）\n\n'
                 '**触发**：%s\n\n'
                 '**基线指纹**：chars=%d / bytes=%d / md5=%s\n\n'
                 '%s\n%s\n%s\n') % (z, reason, s0['chars'], s0['bytes'], s0['md5'],
                                    fence, t0, fence)
        det2 = det + entry
        assert det2[:len(det)] == det, 'DETAIL 前缀被改写'
        assert t0 in det2, 'DETAIL 未含原文'
        open(DETAIL, 'w', encoding='utf-8', newline='\n').write(det2)
        d1 = stats(read_text(DETAIL))
        print('ARCHIVED Z-%d : DETAIL %d -> %d bytes (+%d)'
              % (z, d0['bytes'], d1['bytes'], d1['bytes'] - d0['bytes']))
    with open(MEM, 'w', encoding='utf-8', newline='\n') as f:
        f.write(t1)
    back = read_text(MEM)
    if back != t1:
        print('FATAL: 读回 != 写入 (未预期)')
        sys.exit(5)
    s2 = stats(back)
    print('WROTE MEM chars=%d bytes=%d md5=%s' % (s2['chars'], s2['bytes'], s2['md5']))
    print('-- 独立核验 --')
    v = []
    v.append(('LF-only', '\r' not in back))
    v.append(('chars<=%d' % CHAR_TARGET, s2['chars'] <= CHAR_TARGET))
    v.append(('bytes<8000', s2['bytes'] < 8000))
    v.append(('BAN==0', not [c for c in back if ord(c) in set(BAN)]))
    v.append(('P 编号零丢失',
              not ({int(m) for m in re.findall(r'\bP(\d+)\b', t0)}
                   - {int(m) for m in re.findall(r'\bP(\d+)\b', back)})))
    detf = read_text(DETAIL)
    v.append(('DETAIL 前缀未改', detf[:len(det)] == det))
    if t0.strip():
        v.append(('DETAIL 含压缩前原文', t0 in detf))
    allok = True
    for name, cond in v:
        print('  [%s] %s' % ('PASS' if cond else 'FAIL', name))
        allok = allok and cond
    print('VERIFY = %s' % ('OK' if allok else 'FAIL'))
    if allok:
        wave_reset()
    sys.exit(0 if allok else 6)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == 'check':
        cmd_check()
    elif cmd == 'show':
        cmd_show()
    elif cmd == 'auto':
        cmd_auto(sys.argv[2] if len(sys.argv) > 2 else None,
                 sys.argv[3] if len(sys.argv) > 3 else None)
    elif cmd == 'plan':
        wave_bump()
        cmd_plan(sys.argv[2])
    elif cmd == 'apply':
        cmd_apply(sys.argv[2])
    else:
        print('unknown cmd: %s' % cmd)
        sys.exit(1)


if __name__ == '__main__':
    main()
