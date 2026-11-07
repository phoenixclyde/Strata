# -*- coding: utf-8 -*-
"""W828n: audit "is everything that was adopted actually in production?"
Reads the register (ADOPTED rows), extracts --flags / STRATA_* tokens from name+value,
and compares with the live production config."""
import io, json, re

REG = 'D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv'
PROD = json.load(io.open('D:/workbuddy_space/strata_ws/albus/w828/prod_cfg.json', encoding='utf-8'))
args, env = PROD['args'], PROD['env']

raw = [l for l in io.open(REG, encoding='utf-8').read().split('\n') if l.strip()]
rows = [r.split('\t') for r in raw[1:]]
tok = re.compile(r'(STRATA_[A-Z0-9_]+|--[a-z][a-z0-9-]+)')

ok, missing, mismatch, na = [], [], [], []
for r in rows:
    if len(r) < 6 or r[5].upper() not in ('ADOPTED',):
        continue
    txt = ' '.join(x for x in (r[2], r[3]) if x)
    toks = sorted(set(tok.findall(txt)))
    if not toks:
        na.append((r[0], r[2][:60]))
        continue
    for t in toks:
        if t.startswith('STRATA_'):
            if t in env:
                ok.append((r[0], t, env[t]))
            else:
                missing.append((r[0], t, '—'))
        else:
            if t in args:
                ok.append((r[0], t, args[t]))
            else:
                missing.append((r[0], t, '—'))

print('ADOPTED rows audited; tokens found: %d  present: %d  absent: %d  rows w/o config token: %d'
      % (len(ok) + len(missing), len(ok), len(missing), len(na)))
print()
print('=== ABSENT from production config ===')
for pid, t, _ in missing:
    print('  %-6s %s' % (pid, t))
print()
print('=== present (spot list) ===')
for pid, t, v in ok:
    print('  %-6s %-34s %s' % (pid, t, v))
print()
print('=== ADOPTED rows that name no config token (build/pack/choice) ===')
for pid, nm in na:
    print('  %-6s %s' % (pid, nm))
