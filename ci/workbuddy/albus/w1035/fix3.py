#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1035 §12：把钩子首夜的修正如实写进报告与 P410。"""
import io

REP = "albus/w1035/reply.md"
PROG = "deploy/PROGRESS.tsv"

SEC = (
    "\n**12. 钩子上线当晚的三次修正（含一次我自己的误判）。** "
    "① **「误判」这条是我看错**：`Stop` 钩子第一次触发时我判它「抓错了」，实际它拦的是「编号清单」那条回复"
    "——那条确实没有四段，**它抓对了**。"
    "② **真 bug 是乱码**：JSON 里直接写中文，宿主按 GBK 解析，`reason` 全成方块 ⇒ 改 `ensure_ascii=True`，"
    "输出纯 ASCII 转义，任何代码页都不会坏。"
    "③ **补了 fail-open 与探针**：payload 没有 `last_assistant_message` 时不再据此判负（改看本轮报告是否比标记新，"
    "两者都拿不到就放行），每次调用把 `cwd / stop_hook_active / msg_len / keys` 追加到 `.workbuddy/.hook_seen.log`；"
    "四分支已于本地复测（无字段→放行、无四段→block、有四段→放行、`stop_hook_active`→放行）。"
    "**仍待实测**：桌面版到底给不给 `last_assistant_message`——看下一次 `.hook_seen.log` 的 `keys=` 一行就知道。\n"
)

NOTE = (
    "  **钩子首夜修正**：真 bug 是输出乱码（UTF-8 按 GBK 读）⇒ `ensure_ascii=True`；补 fail-open"
    "（payload 无 `last_assistant_message` 时不据此判负）与探针 `.workbuddy/.hook_seen.log`；"
    "四分支复测通过。**首次触发被判成「抓错」是我的误判**——它拦的那条回复确实没有四段。"
)


def main():
    rep = io.open(REP, encoding="utf-8").read()
    if "12. 钩子上线当晚的三次修正" not in rep:
        io.open(REP, "w", encoding="utf-8", newline="\n").write(rep.rstrip("\n") + "\n" + SEC)
        print("reply.md +§12")

    prog = io.open(PROG, encoding="utf-8").read()
    lines = prog.rstrip("\n").split("\n")
    for i, l in enumerate(lines):
        if l.split("\t")[1:2] == ["P410"]:
            if "钩子首夜修正" not in l:
                lines[i] = l + NOTE
                print("P410 +hook fix")
            break
    io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
