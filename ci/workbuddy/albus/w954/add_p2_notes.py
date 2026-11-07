# -*- coding: utf-8 -*-
'''Append a short 口径注记 to the 7 docs whose P2 items are numeric/scope nits (no fragile anchors).'''
import io

D = 'D:/workbuddy_space/strata_ws/deploy/'
NOTES = {
 'W941_PREFILL_800_REOPEN.md':
  '**每秒口径**：§1 的「801.4 tok/s」应写日志原值 —— `60330 / 75030 ms = 804.1`、`60008 / 74987 ms = 800.2`，'
  '中位 **802.2**（CV 0.085%）。801.4 是早一版草稿的笔误，不影响任何结论。',
 'W932_R75_AND_CHUNK16384_ADOPT.md':
  '**两种口径别混**：§87 的「130K 档快 8.1%」是**吞吐**口径，同一行的 177.9→165.1 s 是**时长**口径（7.2%）。'
  '以后引这一行要写清用哪个。',
 'W931_R70_CHUNK_SCAN.md':
  '**判据缺口**：§41「16K 档 16384 快 2.61%」而该 run 的 CV 上限 1.4% ⇒ 2×CV = 2.8% **大于**效应本身，按现行判据不算成立。'
  '该结论现已被 `W932` 的六长度表（全 `0 reused`、加权 +2.2%）取代。另 §43 的 64K/8192 臂被 `W932 §3` 判为受前缀复用污染。',
 'W933_R76_PARTIAL_PREFIX.md':
  '**复算**：§29「turn1 上 16384 快 7.5%」按同段两个数应为 `1 − 32.1/34.5 = 6.96%`；7.5% 高估 0.5pp，不影响"保留 16384"的结论。',
 'W929_M3_K8V8_PREFILL.md':
  '**判否的依据要分清**：prefill 零差异是**实测**（1202→1211 ms，+0.75%，3 次重启），'
  '但 M3 判否的决定性代价（decode −1.1~−2.3%）是**按槽数线性外推**、从未跑 decode A/B。'
  '若将来 decode 侧需要更省显存，这一条要重开验证。',
 'W930_R69_PENALTY_WINDOW.md':
  '**灵敏度**：§75-101 的「0/9 + 0/9 不复现」是在**贪心 T=0** 下取的 3 次请求 = 确定性单样本，'
  '灵敏度远低于上游的 32 seeds。结论（症状不复现）成立，但"已证伪"的强度只到"本场景未观察到"。',
 'W935_PLE_RAISE_LIMIT_ADOPT.md':
  '**代理件**：§38-52 的 A 档（8→1536 MiB、mlock 512）是用**复刻补丁逻辑的小程序**测的，不是真实二进制 in-situ；'
  '生产 `unlimited` 档完全静默这一点是实测（两臂 rep6–9），不受影响。',
}
for name, note in NOTES.items():
    p = D + name
    s = io.open(p, encoding='utf-8').read()
    if '【AUDIT24 口径注记】' in s:
        print(name, 'already')
        continue
    s = s.rstrip() + '\n\n---\n\n** 【AUDIT24 口径注记】**\n' + note + '\n'
    s = s.replace('** 【AUDIT24 口径注记】**', '**【AUDIT24 口径注记】**')
    io.open(p, 'w', encoding='utf-8', newline='').write(s)
    print(name, 'noted')
