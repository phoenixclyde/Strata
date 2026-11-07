# 记 W714x/W714y：链接治理完成（机主裁定：现役暂不切 + 充分利用软连接 + MTP 复用）
import io

LOG = r"D:/workbuddy_space/strata_ws/.workbuddy/memory/2026-10-08.md"
note = """
## W714x/W714y 链接治理（2026-10-09 01:0x-01:1x）
- **机主裁定**：现役**暂不切换**（保留 base）；布局**充分利用软连接**；**MTP 复用现成那份**（huihui 仓不提供 MTP）。
- **新发现（重要）**：/home/albus/strata166/weights **本身就是目录软链** -> /models/unsloth/Qwen3.8-Flash-Next-UD-IQ4_XS。
  此前我把它读成"硬链接同 inode"，是因为 `ls -li` 带尾斜杠时看到的是目录内容 => 旧容器挂 /weights 与 /models 实为同一份。
- **实体唯一化**（删名前 fail-closed 校验两侧全量 sha256 逐字节相同，再动手）：
  - $U/mmproj-Qwen3.8-Flash-Next-BF16.gguf（907 MB 实体）=> 软链指向 huihui 目录的实体，**释放 907 MB**；
  - huihui/unsloth-UD-IQ4_XS/00001（10.9 MB 实体）=> 软链指向 /models/unsloth/.../00001（两仓逐字节相同），**释放 10.9 MB**；
  - huihui/mtp => 软链指向 /home/albus/strata166/data/mtp（宿主路径；容器内对应 /data/mtp）。
  合计释放约 918 MB。
- **终态自证**：软链解析 4/4 全绿；sha256 抽验 c67b468b / 130560b6（huihui 两片）、5ce89370（两仓同）、b1a82259（mmproj）全对；
  现役容器 strata166-406 未受影响（仍 Up）。166 盘：934 GiB 总 / 771 GiB 用 / 162.9 GiB 余。
- **留下的布局要点**（写进了 /models/huihui-ai/.../PROVENANCE.md 第五节，5044 B）：
  /models/unsloth 三片是实体（base，现役在用）；huihui 目录 mmproj+00002+00003 是实体、00001 与 mtp 是软链；/weights 是目录软链。
- **仍待机的事项**：切换现役到 huihui 的完整链路（iq_pack 重生成 pack -> 改 config -> 新容器 -> 重跑 profile -> 重测；
  现行读数作废；MTP 为 base 派生，换主模型后接受率需重测）。机主已发话"暂不切"，等其择时。
"""
io.open(LOG, "a", encoding="utf-8", newline="\n").write(note)
back = io.open(LOG, encoding="utf-8").read()
BAN = [0x21D2, 0x2192, 0x2014, 0x2013, 0x2026, 0x2265, 0x2264, 0x2260, 0x2212, 0x00D7]
bad = [hex(ord(c)) for c in note if ord(c) in BAN]
print("追加 %d 字符；文件现 %d 字符；CR=%d；禁用码位=%d" % (len(note), len(back), back.count("\r"), len(bad)))
for k in ["W714x/W714y", "目录软链", "918 MB", "暂不切换", "PROVENANCE.md 第五节"]:
    print("  自证 %-22s %s" % (k, "OK" if k in back else "**缺失**"))
