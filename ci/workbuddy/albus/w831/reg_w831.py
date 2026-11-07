#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Register W831 (monitor width) + the WEB-UI gate false-green correction."""
import io

P = "D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv"
s = io.open(P, encoding="utf-8").read()

rows = [
    ("P203", "UI", "monitor 页去封顶（上游 v0.2.7.1 起 .monitor 封顶 1920px）",
     ".monitor { max-width: none }（serve/web/app.css 末尾，局部补丁 W831）", "ui", "ADOPTED",
     "—", "—", "TEL-PCIE/P202",
     "三棵树 app.css md5 全等 cf027c74…（src0271/src027/src028）+ 容器 + HTTP 下发一致 ⇒ 非我们改动。"
     "上游逐 tag：v0.2.2~v0.2.6 = 1240px，v0.2.7.1/v0.2.8 = min(100%,1920px)。截图反算视口 2560"
     "（缩放 0.4219，用卡片 gap 14px、ctx-gauge 150px、容器 1968px 三点互校）⇒ 1920 第一次咬到。"
     "作用域仅 .monitor，about/chat 保留上游 1100。无头 Chrome 2560×1080 实图：8 卡一行、面板通栏；"
     "1280×900 回落 4 卡一行、无横向滚动。镜像 0.2.8p2。",
     "采纳。若要再收窄，只改这一个数字（例：min(100%, 2400px)），不要动 .about/.chat。"),

    ("P204", "PROCESS", "补丁门禁假绿：WEB-UI 的标记 saveApiKey 上游自带，掩盖了补丁缺失",
     "标记改为 pciePk（真正只属于我们的增量）", "process", "CORRECTED",
     "—", "—", "P201/P202/P203",
     "部署的 app.js 与上游 v0.2.8/v0.2.7.1 字节相同（md5 9fed14d1…，92101 B）⇒ 补丁不在。"
     "把 patched(63395B) − base orig(59958B) 得真实增量 78 行，逐行比对上游：74 行上游已原生具备"
     "（images 页/saveApiKey/prefill 速率/采样默认值/火花线顶值），只有 4 行是我们的 = PCIe 卡 "
     "'· peak NN MB/s' 后缀。门禁之所以绿，是因为 saveApiKey 是上游自己的词。已按 ALBUS-W831 把 4 行补回"
     "（92101→92306B），实测 'to GPU 0.0 MB/s · peak 162 MB/s'；空载 pciePk<1 不显示。"
     "规矩补充：门禁标记必须是「上游不可能也有的字符串」，并同时校验 tree+image+served 三处。",
     "已更正。今后新增补丁，标记一律用 ALBUS-<批次> 前缀，禁止用功能词。"),
]

for r in rows:
    pid = r[0]
    if ("\n" + pid + "\t") in ("\n" + s) or s.startswith(pid + "\t"):
        print(pid, "already present")
        continue
    s += "\t".join(r) + "\n"
    print(pid, "added")

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
raw = [l for l in s.split("\n") if l.strip()]
print("rows now", len(raw), "(incl. header)")
