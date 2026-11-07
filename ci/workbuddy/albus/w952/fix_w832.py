# -*- coding: utf-8 -*-
'''AUDIT24: bring the authoritative plan (W832) back in line with the ledger (W943/W947/AUDIT24).'''
import io

P = 'D:/workbuddy_space/strata_ws/deploy/W832_OPT_PLAN_V2.md'
s = io.open(P, encoding='utf-8').read()
edits = []


def rep(tag, old, new):
    global s
    if old in s:
        s = s.replace(old, new, 1)
        edits.append(tag)
    else:
        edits.append(tag + '-MISS')


rep('637',
    '''> ⇒ 我们上一轮把权重压在"指令层"，实际最大杠杆在 **拷贝/调度层（R88）** 与 **QSA 稀疏 prefill（R89）**，repack（R86）第三。''',
    '''> ⇒ 我们上一轮把权重压在"指令层"，实际最大杠杆在 **拷贝/调度层（R88）**，其次 **repack（R86）**。
> ~~QSA 稀疏 prefill（R89）~~ **【AUDIT24 更正】不是杠杆**：我们的 `qsa_prompt_attn` 早已是 gather-only
> （`n = steps[…]`、`cell = ids[c0+c]`），furnace 的 +85% 是 dense→sparse 的差，对我们不成立；`R89` 现为 OPEN（待实跑确认）。''')

rep('638',
    '''> 另：我们的 llama.cpp 是 **0.4.1**，社区最新已到 **v0.7.0**（exabit merge-v0.7.0, 2026-10-22）—— 三个月里上游对 qwen4exp/GDN/QSA 的修正我们一条没吃。''',
    '''> ~~另：我们的 llama.cpp 是 **0.4.1**，社区最新已到 **v0.7.0** —— 三个月里上游对 qwen4exp/GDN/QSA 的修正我们一条没吃。~~
> **【AUDIT24 更正】版本号不是可比锚点**（`W948` 自查）：`get_J_max` 在上游 master 也是 0 ⇒ 那是我们自己的补丁；
> `3cf03257` 只出现在别人的 bench README。能确认的只有**我们与上游 master 差 587 行**；`R90` 保留，但 S1 先做 pin→tag 映射。''')

rep('651',
    '''> ⇒ **MMQ 五扇门（R51/R58/R60/R63/R84）全关**，prefill 再往上只能走 attention（R46/R64）与 GDN/入口 —— 这就是 R85 的全部空间。''',
    '''> ~~⇒ **MMQ 五扇门（R51/R58/R60/R63/R84）全关**，prefill 再往上只能走 attention（R46/R64）与 GDN/入口 —— 这就是 R85 的全部空间。~~
> **【AUDIT24 更正 2026-11-04 17:0x】这句不再成立**：只有 **R51 / R58** 是"跑过两臂"判否；
> **R60 / R63 已按纪律⑱ 重开（OPEN）**、**R84 = INFLIGHT**（`W947`）；dot8 的接入另立 **R91**（`W951`，P0 数值已跑通）。
> 正确表述：**内层循环/tile 微调这一族关掉了；布局层（R86）、拷贝层（R88）、attention 效率（R46）与 dot8（R91）都还开着。**''')

rep('656',
    '''> 同时把 R84 的依据升级：VALU 67% 忙而供给率只有 36% ⇒ 时间花在辅助指令（dp4a 仅占 53.3%，`W924`）；dot8 砍半该段 ⇒ 总指令 −26.7% ⇒ kernel −17.9% ⇒ **端到端 −3.65%**（> 门 3.2%）。''',
    '''> ~~同时把 R84 的依据升级：…dp4a 仅占 53.3%…端到端 −3.65%~~ **【AUDIT24 更正】整段作废**：53.3% 是**模块口径**
> （多 J / fallback 实例全算）；真 kernel 里 dot4 = 30.0%（`W943`）⇒ 端到端 **−2.05%**。
> 67.1% 本身已由 `AUDIT24` 复测确认为 **67.3%**（同形状 16×1024；生产形状 16×320 是 **60.6%**，`W945`）。''')

rep('794',
    '''**已结 DONE_NEG（`W946` A 级源码）**''',
    '''**OPEN（`W947` 按纪律⑱重开；`W946` 的源码判断只算线索，不算结案）**''')

rep('R86-row',
    '''43/48 层、**88.6% 专家字节**''',
    '''43/48 层（down 内占 **86%**、**专家总字节 35%**；~~88.6%~~ 是 offset 加权且分母指 down，`AUDIT24` 更正）''')

io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('edits:', edits)
