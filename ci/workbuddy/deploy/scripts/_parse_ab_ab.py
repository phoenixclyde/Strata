# -*- coding: utf-8 -*-
"""从 _ab_ab.txt 抽取十臂的关键数字，输出对照表。"""
import os, re, sys
sys.stdout.reconfigure(encoding='utf-8')

P = r'D:\strata166\logs\_ab_ab.txt'
t = open(P, encoding='utf-8', errors='replace').read()

# 按 ARM 切块
blocks = re.split(r'^### ARM ', t, flags=re.M)[1:]
rows = []
for b in blocks:
    label = b.split()[0]
    def find(pat, cast=float, grp=1, default=None):
        m = re.search(pat, b)
        if not m:
            return default
        try:
            return cast(m.group(grp))
        except Exception:
            return m.group(grp)
    tok = find(r'prefill 16383 tokens in \d+ chunks, [\d.]+ ms \(([\d.]+) tok/s\)')
    ms = find(r'prefill 16383 tokens in \d+ chunks, ([\d.]+) ms')
    ple = find(r'; PLE ([\d.]+) ms')
    dma = find(r'\((\d+) by DMA', int)
    hostm = find(r'host ([\d.]+) ms\)')
    slots = find(r'expert cache (\d+) slots', int)
    resid = find(r'resident RAM mode: ([\d.]+) GiB')
    pool = find(r'CPU expert pool\s+([\d.]+) ms/token')
    rows.append(dict(label=label, tok=tok, ms=ms, ple=ple, dma=dma, hostm=hostm,
                     slots=slots, resid=resid, pool=pool, ok=tok is not None))

print('%-18s %8s %10s %9s %9s %7s %9s %8s' %
      ('ARM', 'tok/s', 'prefill_ms', 'PLE_ms', 'host_ms', 'slots', 'resident', 'pool ms/tk'))
print('-' * 88)
for r in rows:
    if not r['ok']:
        print('%-18s %8s %10s %9s %9s %7s %9s %8s   ← 无分解行（该臂未跑到预填）'
              % (r['label'], '-', '-', '-', '-', r['slots'] or '-', r['resid'] or '-', '-'))
        continue
    print('%-18s %8.1f %10.1f %9.1f %9.1f %7d %9.2f %8.2f' %
          (r['label'], r['tok'], r['ms'], r['ple'], r['hostm'], r['slots'], r['resid'], r['pool']))

base = next((r for r in rows if r['label'].startswith('A1') and r['ok']), None)
if base:
    print()
    print('=== 相对 A1_base（%.1f tok/s）===' % base['tok'])
    for r in rows:
        if r['ok'] and r is not base:
            print('  %-18s %+6.2f%%   (%.1f tok/s)' % (r['label'], (r['tok'] / base['tok'] - 1) * 100, r['tok']))
