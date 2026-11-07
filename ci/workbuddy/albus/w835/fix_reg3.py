import io, shutil

P = 'D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv'
shutil.copy2(P, P + '.bak-w835')
raw = io.open(P, encoding='utf-8').read().split('\n')

# ---- 1) pull the 4 narrative lines out (they are not data rows) ----
orphans = [(n, l) for n, l in enumerate(raw) if l.strip() and l.count('\t') == 0]
keep = [l for n, l in enumerate(raw) if not (l.strip() and l.count('\t') == 0)]

O = 'D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER_ORPHAN_LINES.md'
o = ['# PARAM_REGISTER.tsv 里的叙事行（不是数据行，2026-10-31 由 albus 移出）',
     '',
     '这 4 行是 W823/W824 时期误写进 TSV 的叙述段落，各占 1 列，会让任何按 11 列解析的脚本出错。',
     '内容原样保留在下面，未做任何编辑。',
     '']
for n, l in orphans:
    o.append('- (原第 %d 行) %s' % (n + 1, l))
    o.append('')
io.open(O, 'w', encoding='utf-8', newline='\n').write('\n'.join(o))

# ---- 2) rebuild P222 as a proper single-line 11-column row ----
keep = [l for l in keep if not l.startswith('P222')]
EV = ('5 臂（base / +ATTN_LANECELL / +TSUM / +MERGE_V2+EXPDEC / base2 复测），每臂 8x128 tok decode + 3 档 read。 '
      'decode 中位：base 51.65、base2 51.70、tL 51.60、tLT 51.60、tL4 51.70 ⇒ 四项全部零收益。 '
      'read 6666 tok：base 9707、base2 9708（复现 0.01%）、tL 10156(+4.6%)、tLT 10199(+5.1%)、tL4 10123(+4.3%)。 '
      'tL 单项已退化、再叠加另三项无进一步变化 ⇒ 退化由 ATTN_LANECELL 单项造成。三个长度均退化且随长度放大'
      '（+1~2% / +2~3% / +4.3~5.1%），是 attention 相位的真实成本。 '
      '对照 gfx12 表声明的 ATTN_LANECELL+MERGE_V2 +1.9%、TSUM +1.9%、EXPDEC +0.6%、四项合计 +3.5% bitwise。 '
      '教训：bit-identical 只保证答案不变，不保证不变慢；arch_defaults 每一行都是本卡实测，不可从别卡推导。')
row = ['P222', 'MEASUREMENT',
       '四项 gfx12 上的 bitwise 开关在 gfx906 上实测：decode 0 收益，prefill 退化 4-5%',
       '全部不采用；新增纪律：别的架构的开关一律按未知处理、先单项测',
       'measurement', 'REJECTED', '—', '—', 'P221', EV,
       '不采用；生产不变']
assert len(row) == 11, len(row)
keep.append('\t'.join(row))

io.open(P, 'w', encoding='utf-8', newline='\n').write('\n'.join([l for l in keep if l is not None]).rstrip('\n') + '\n')

raw2 = [l for l in io.open(P, encoding='utf-8').read().split('\n') if l.strip()]
bad = [(n, l.count('\t') + 1) for n, l in enumerate(raw2) if l.count('\t') != 10]
print('rows:', len(raw2) - 1)
print('rows with != 11 cols:', bad if bad else 'none')
print('orphans moved:', len(orphans), '->', O.split("/")[-1])
print('last:', repr(raw2[-1][:100]))
