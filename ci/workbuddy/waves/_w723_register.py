# -*- coding: utf-8 -*-
"""W709 步13：把 calibrate 的实测结论落进 PARAM_REGISTER.tsv（唯一真值）
- P06 --spec-min-p  0.5  -> 0.70
- P25 --pcie-frac  CALIBRATED -> 0.20（并挪到 P05 之前，保证取值型参数不在末位）
- P26 --pool-workers  CANDIDATE -> REJECTED（实测 21=默认 最优）
- P27 adapt 三件      CANDIDATE -> REJECTED（实测 default 最优）
- P24 calibrate       CANDIDATE -> ADOPTED（已跑，929 s）
附：P06/P25 带校准原始 sweep 数字。
"""
import io, os, shutil, time, hashlib

HERE = r'D:/strata166/params'
REG = os.path.join(HERE, 'PARAM_REGISTER.tsv')
EV = os.path.join(HERE, 'evidence')
os.makedirs(EV, exist_ok=True)

# --- 备份 ---
bak = REG + '.bak_w709_' + time.strftime('%Y%m%d_%H%M%S')
shutil.copy2(REG, bak)
b0 = open(REG, 'rb').read()
print('backup ->', bak, '| before: %d B md5=%s CR=%d' % (len(b0), hashlib.md5(b0).hexdigest(), b0.count(b'\r')))

raw = io.open(REG, encoding='utf-8-sig').read()
lines = raw.splitlines()
hdr = lines[0].split('\t')
assert hdr[0] == 'id' and len(hdr) == 11, hdr


def upd(row_id, **kw):
    """按 id 找到行，更新字段（按列名）。返回该行的 dict。"""
    for i, ln in enumerate(lines):
        f = ln.split('\t')
        if f[0] == row_id:
            d = dict(zip(hdr, f))
            d.update(kw)
            lines[i] = '\t'.join(d[c] for c in hdr)
            return d
    raise SystemExit('id not found: %s' % row_id)


EV_P25 = ('calibrate 929s 实测：PCIe 份额 0.00=35.19/0.20=35.68/0.35=32.76/0.36(原auto)=33.71/'
          '0.55=30.95/0.75=29.05；交错确认(各3次) 0.36/0.5 中位33.73 vs 0.20/0.7 中位37.42 = +10.9%；'
          '独立交错A/B复核 +9.0%（42.95 -> 46.8）；预填不变(455.55/455.80)')
EV_P06 = ('calibrate 草稿门槛 sweep 0.3=33.74/0.5=35.72/0.7=36.96；与 --pcie-frac 0.20 联合交错确认 '
          '3×3 中位 37.42 vs 默认 33.73 = +10.9%；独立 A/B 复核 +9.0%')
EV_P26 = 'calibrate 实测：21(=引擎默认)=36.0 / 14=34.8 / 10=34.2 / 5=29.1 => 默认最优，不改'
EV_P27 = 'calibrate 实测（512-token 生成）：default=39.7 / 1-80-0.97=33.6 / 1-160-0.97=33.4 => 默认最优，不改'
EV_P24 = 'W709 已跑：929 s，独立窗口（临时容器 strata-calib），settings={--pcie-frac 0.20, --spec-min-p 0.70}'

upd('P06', value='0.70', evidence=EV_P06, verdict='calibrate 实测采纳（+10.9%，独立复核 +9.0%）')
d25 = upd('P25', value='0.20', status='ADOPTED', evidence=EV_P25, verdict='calibrate 实测采纳（唯一 >3% 门槛的解码旋钮）')
upd('P26', status='REJECTED', evidence=EV_P26, verdict='实测默认(21)最优 => 不采用')
upd('P27', status='REJECTED', evidence=EV_P27, verdict='实测引擎默认最优 => 不采用')
upd('P24', status='ADOPTED', evidence=EV_P24, verdict='已执行（唯一入口：tools/calibrate.py）')

# --- 把 P25 行挪到 P05 行之前（保证 --pcie-frac 的取值不在 args 末位）---
i25 = next(i for i, ln in enumerate(lines) if ln.split('\t')[0] == 'P25')
row25 = lines.pop(i25)
i05 = next(i for i, ln in enumerate(lines) if ln.split('\t')[0] == 'P05')
lines.insert(i05, row25)

out = ('\n'.join(lines) + '\n').encode('utf-8')
assert out.count(b'\r') == 0
assert not out.startswith(b'\xef\xbb\xbf')
open(REG, 'wb').write(out)
print('after: %d B md5=%s CR=%d lines=%d' % (len(out), hashlib.md5(out).hexdigest(), out.count(b'\r'), len(lines) - 1))
print()
# 列数自检
bad = [(i + 1, len(x.split('\t'))) for i, x in enumerate(lines) if x.strip() and len(x.split('\t')) != 11]
print('列数异常 =', bad or 'none')
import collections
print('status 分布 =', dict(collections.Counter(x.split('\t')[5] for x in lines[1:] if x.strip())))
print()
print('--- 改动行 ---')
for rid in ('P05', 'P25', 'P06', 'P26', 'P27', 'P24'):
    for ln in lines:
        f = ln.split('\t')
        if f[0] == rid:
            print('  %-4s %-26s %-12s %-9s %s' % (f[0], f[2], f[3], f[5], f[10][:70]))
print()
print('--- args 顺序（模拟 gen_config 的取法）---')
args = []
for ln in lines[1:]:
    f = ln.split('\t')
    if f[5] != 'ADOPTED' or f[1] != 'CLI':
        continue
    if f[3] == '(flag)':
        args.append(f[2])
    else:
        args += [f[2], f[3]]
print('  ' + ' '.join(args))
