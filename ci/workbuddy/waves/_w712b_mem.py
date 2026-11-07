# 追加今日日志：原件删除完成 + 一条本机缺陷
import io, time

p = r"D:/workbuddy_space/strata_ws/.workbuddy/memory/2026-10-08.md"
note = """
## W712b 原件删除（2026-10-08 20:3x ~ 21:0x，机主批准"按照你说的办"）
- 删掉 `D:\\strata166`（6,698 文件 / 219,152,974 B）与 `D:\\workbuddy\\_z_rk81`（165 文件 / 582,840 B）。两处均已不存在。
- 删除前 fail-closed 三件：① 逐文件重算两侧 (字节数, md5)，判据 **源 ⊆ 目标**（不再要求文件集一致，因迁移后有新增件）；
  ② 两个白名单件（目标侧是有意更新过的版本）**删除前快照**并断言 md5 相等；③ 分批 50 个文件删除 + 逐文件 manifest。
- 实测：strata166 6,697/6,698 逐字节相同 + 1 白名单；_z_rk81 164/165 + 1 白名单；白名单内差异 = 0 个意外。
- 快照（留档）：`tools/snapshots_premigrate/strata166/configs/workbuddy-strata166.md`（7,324 B / md5 f7e5e2ae34516e8ccabeb8d17a71b097）、
  `tools/snapshots_premigrate/_z_rk81/_gh.py`（3,042 B / md5 84e9897ec4e515c31b13b53ecd0a064f）。
- 证据：`tools/_predelete_report.md`、`tools/_delete_manifest_*.txt`、`tools/_predelete_run{,2}.out.txt`。
- 执行器：`tools/_predelete_verify_and_delete.py`（--go）、`tools/_finish_predelete.py`（收尾 116 个文件）。
- **坑（已升为跨项目教训，写进用户级记忆第 11 条）**：文件删完后用 Python 逐目录 `os.rmdir` 清 739 个空目录走了约 12 分钟
  （约 0.7 s/目录，经本机安全垫片），表现与"卡死"完全一样；机主问"卡死了？"，我误判并杀了进程（实际仍在推进）。
  改用 PowerShell `Remove-Item -Recurse -Force` 秒级收尾。**判别法：先看被删对象自身（文件数/目录数）与输出文件大小是否在变。**
- 文档同步：`MAP_OLD_TO_NEW.md` 新增第六节（含白名单、快照、坑）；`PROJECT.md` 第六节标注两处旧路径已删。
"""

with io.open(p, "a", encoding="utf-8", newline="\n") as f:
    f.write(note)
print("appended", len(note), "chars")
