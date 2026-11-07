# -*- coding: utf-8 -*-
'''AUDIT24: record the second-round (conclusion-level) retractions in the audit doc.'''
import io

p = 'D:/workbuddy_space/strata_ws/deploy/AUDIT24_W900_W951.md'
s = io.open(p, encoding='utf-8').read()
anchor = '---\n\n## 2 P2（12 条，已改 8 处）'
add = '''### 1.1 第二轮：横幅加了、结论没撤的四处（子审计复核后补）

第一轮横幅多数只改了"数字口径"，但有四处的**结论本身**还立着，等于读者仍会按旧的走。已补：

| 位置 | 现象 | 补法 |
|---|---|---|
| `W942` | 横幅只讲 67.1% 的复现与形状，**R60 / R84 = DONE_NEG 仍立着** | 明写「数字保留、由它推出的两条关闭不保留」，R60/R63 → OPEN、R84 → INFLIGHT |
| `W944 §60` | 横幅末句写「端到端预期与 R86 排序**不变**」，与 `W945` 的「0 ~ −6.3% 未知」互斥 | 改成「−6.3% 已下调为 0 ~ −6.3% 未知，只有 13.8% 这个分母不变」 |
| `W946 §6/§7` | 横幅只改了两个数字，R89 仍写「当场判否（A 级源码）」，与 `W832:803` 的 OPEN 矛盾 | 补「源码阅读按 `W939 §0` 是 D 级；R89 已改回 OPEN，待 depth 1×/3×/6× 实测」 |
| `W947 §50-57` | 猜的根因是 `_Float16`，`W950/W951` 已证否（缺 warp 归约），无横幅 | 补横幅：根因 = 缺 warp 归约 + host 参考多乘 scale；修正后 0.00319 / 0.06481 |

**判据（写进纪律㉔）**：撤回横幅必须包含**结论动词**（"关闭不保留 / 改回 OPEN / 上限不作预期"），
只写"数字口径更正"不算撤回 —— 本轮 4 处全是这个形态。

**另记一条验证陷阱**：`|Δ|` 转义成 `\\|Δ\\|` 之后，`awk -F'|'` 仍把它当分隔符，
所以"字段数 = 9"不再能判破表；只能用 `grep -c '|Δ|'`（应为 0）。本轮三位读者先后用错这个判据。

---

## 2 P2（12 条，已改 8 处）'''
if '1.1 第二轮' not in s:
    s = s.replace(anchor, add, 1)
    io.open(p, 'w', encoding='utf-8', newline='').write(s)
    print('audit doc: section 1.1 added')
else:
    print('already there')
