import io

p = 'D:/workbuddy_space/strata_ws/deploy/W787_R1_FAILURE_REVIEW.md'
lines = io.open(p, encoding='utf-8').read().split('\n')

new_line = ('所以 `W786 §4` 把 GEMV（13.3%）/ router（8.1%）/ HC（16.1%）降到「端到端 0.2-0.4%」是**错的**。'
            '**但要写准（`AUDIT7 P2-4`）**：13.3% / 8.1% / 16.1% 是 **decode 内部**占比；只有当 decode 占端到端约 99%'
            '（输出 >=300 token）时它们才近似等于端到端占比，48 token 输出时 decode 只占 1.0/1.69 = 59%，'
            '对应端到端约 **7.9% / 4.8% / 9.5%**。结论不变（比 0.2-0.4% 高一个数量级），但引用必须带条件。')

hit = 0
for i, ln in enumerate(lines):
    if ln.startswith('所以 `W786 §4` 把 GEMV'):
        lines[i] = new_line
        hit += 1

assert hit == 1, hit
io.open(p, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))
print('W787 line 78 replaced')
