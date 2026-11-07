import io

p = ".workbuddy/memory/2026-11-07.md"
add = """
- **kvg.on 是第二组条件（P478）**：`generate.cpp:9961` 比「弹性 K/V 已开」多 `xcache.vmm_range()` / `d_res` / `host_res` / `srcp` / `top > floor` 五项；为假时 `kvg_ensure` 开头 `if (!kvg.on ...) return true` 会**「成功」但不增长** ⇒ 长请求踩未映射 cell。窗口脚本因此先 `grep -aq "elastic K/V:"`，不成立就在发长请求前中止并还原。
"""
io.open(p, "a", encoding="utf-8", newline="\n").write(add)
print("mem ok")
