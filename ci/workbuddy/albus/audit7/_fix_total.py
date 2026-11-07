import io

D = 'D:/workbuddy_space/strata_ws/deploy/'

# ---- W786：合计列改单次 46.13，与分项/每token 同源 ----
p = D + 'W786_TARGET_CORRECTION.md'
s = io.open(p, encoding='utf-8').read()

old_tot = '| **合计** | **46.35** | **47.35** | **39.90** |'
new_tot = '| **合计** | **46.13**（四次运行中位 46.35，见注） | **47.35** | **39.90** |'
assert s.count(old_tot) == 1, s.count(old_tot)
s = s.replace(old_tot, new_tot, 1)

old_note = '自校验（**AUDIT7 P2-2 更正**）：按表内印刷值求和为 **46.11 / 47.34 / 39.81**。'
new_note = ('自校验（**AUDIT7 P2-2 更正，二次修正**）：M 列「合计」已由 46.35 改为 **46.13**（单次运行），'
            '使**分项、合计、百分比、每 token 四者同源**；按印刷值求和为 **46.11 / 47.34 / 39.90**，'
            '与合计差 **-0.02 / -0.01 / 0.00**，与本节声称的自校验一致。'
            '**46.35 是四次运行（46.13/46.44/46.90/46.26）的中位数**，作为 `P91` 的基线值另行记录，不再混进本表。')
assert s.count(old_note) == 1, s.count(old_note)
s = s.replace(old_note, new_note, 1)

# 删掉上一版里已过时的解释句（关于 46.11 与 46.35 差 0.24 的那段）
stale = ('M 列的 `-0.02` 是对**单次运行 46.13** 成立，而本表「合计」列写的是**四次运行的中位数 46.35**'
         '（`46.13 / 46.44 / 46.90 / 46.26`），两者差 0.24 来自「中位数 vs 单次」，不是算错；'
         'L 列原写 3.01 时差 0.09，已补为 3.10。')
s = s.replace(stale, 'L 列原写 3.01 时差 0.09，已补为 3.10。', 1)

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('W786 total -> 46.13, note rewritten')

# ---- register P91：点明每 token 13.85 与中位 46.35 不同源 ----
R = D + 'params/PARAM_REGISTER.tsv'
lines = io.open(R, encoding='utf-8-sig').read().splitlines()
out, hit = [], 0
for i, ln in enumerate(lines):
    f = ln.split('\t')
    if f[0] == 'P91' and i > 0:
        f[9] += (' 【补充】每 token 13.85 是按**单次 46.13 / 3.33 token** 算的，与"总 46.35"（四次中位）不同源；'
                 '`W786 §2.1` 的合计列已改 46.13 使四者同源，46.35 仅作基线中位数保留。')
        out.append('\t'.join(f))
        hit += 1
    else:
        out.append(ln)
assert hit == 1, hit
io.open(R, 'w', encoding='utf-8', newline='\n').write('\n'.join(out) + '\n')
print('P91 note appended')
