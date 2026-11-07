# -*- coding: utf-8 -*-
"""W709 步20：register —— P21 否；新增 P34（--prompt-cache-every 8192 采纳）"""
import io, os, shutil, time, hashlib, collections

REG = r'D:/strata166/params/PARAM_REGISTER.tsv'
bak = REG + '.bak_w709c_' + time.strftime('%Y%m%d_%H%M%S')
shutil.copy2(REG, bak)
b0 = open(REG, 'rb').read()
print('backup ->', os.path.basename(bak), '| before %d B md5=%s' % (len(b0), hashlib.md5(b0).hexdigest()))

lines = io.open(REG, encoding='utf-8-sig').read().splitlines()
hdr = lines[0].split('\t')
assert len(hdr) == 11, hdr

EV21 = ('W709 交错 A/B（18,083-token prompt，各 2 轮）：温 TTFT 5.787(B) vs 5.828(A)，'
        '且 reused 恒为 16384 两臂相同 => 无效果。原因：--prompt-cache-every 默认 16384 已在同一位置放了 '
        'checkpoint，tail 冗余；help 原文亦要求"an existing chunk boundary"')
upd = {
    'P21': dict(status='REJECTED', evidence=EV21,
                verdict='实测无效果（与 --prompt-cache-every 重复）=> 不采用'),
}
done = set()
for i, ln in enumerate(lines):
    f = ln.split('\t')
    if f[0] in upd:
        d = dict(zip(hdr, f)); d.update(upd[f[0]])
        lines[i] = '\t'.join(d[c] for c in hdr); done.add(f[0])
assert done == set(upd), done

# 新行 P34（插在 P20 之前：取值型参数不能排在 args 末位，否则核验器的 next-token 判定会 FAIL）
EV34 = ('W709 交错 A/B（~10,000-token prompt；"温" = 同 prompt 末尾追加一句再发）：'
        '默认 16384 -> reused=0、温 TTFT 23.07/23.07s（两轮）；8192 -> reused=8192、温 TTFT 5.86/5.88s = **-74.6%**；'
        '对照 4096 -> reused=0（无效）。机制：可复用前缀须与 prefill chunk(8192) 对齐。'
        '成本：checkpoint 计入 --prompt-cache N(=6) 上限（help：~118 MB/个）=> 上限约 0.7 GB RAM')
VD34 = '采纳：默认值让 8k~16k-token 会话完全没有多轮复用；8192 把它打开'
row34 = '\t'.join(['P34', 'CLI', '--prompt-cache-every', '8192', 'session', 'ADOPTED',
                   '-', '-', 'P33', EV34, VD34])
i20 = next(i for i, ln in enumerate(lines) if ln.split('\t')[0] == 'P20')
lines.insert(i20, row34)

out = ('\n'.join(lines) + '\n').encode('utf-8')
assert out.count(b'\r') == 0 and not out.startswith(b'\xef\xbb\xbf')
open(REG, 'wb').write(out)
print('after  %d B md5=%s CR=%d 行=%d' % (len(out), hashlib.md5(out).hexdigest(), out.count(b'\r'), len(lines) - 1))
bad = [(i + 1, len(x.split('\t'))) for i, x in enumerate(lines) if x.strip() and len(x.split('\t')) != 11]
print('列数异常 =', bad or 'none')
print('status =', dict(collections.Counter(x.split('\t')[5] for x in lines[1:] if x.strip())))
print()
print('--- ADOPTED 的 CLI args 顺序（模拟 gen_config）---')
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
