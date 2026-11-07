# 记录：W714 模型落位（只读侦察 + 已完成部分）+ 当日日志
import io, os

WS = r"D:/workbuddy_space/strata_ws"
log = os.path.join(WS, ".workbuddy", "memory", "2026-10-08.md")
note = """
## W714 新下载模型落位（2026-10-08 23:47-23:55，机主令：「弄到 166，放 /models，按其中的规则存放；你现在用的删掉」）
- **找到**：`D:\\Qwen3.8-Flash-Next-UD-IQ4_XS\\`（自明目录名）= 3 分片 + **`mmproj-Qwen3.8-Flash-Next-BF16.gguf` 907.54 MB**（vision）。合计 94.6 GB。
- **`/models` 的规则（读出来）**：ModelScope 缓存布局 `{发布者}/{仓库名}/…`（如 `bartowski/Ornith-1.5-35B-A3B-GGUF/`、
  `dealignai/…/mmproj-*.gguf`），另有一级 `.msc` 与 `.lock/{owner}___{repo}`。=> 落点取 `/models/unsloth/Qwen3.8-Flash-Next-UD-IQ4_XS/`
  （沿用机主自明目录名；外部查 HF/MS 仓库名两次都失败：HF 502、MS 搜索口 404，若要改名是一条命令的事）。
- **已落位（本期只做安全部分）**：建目录；3 分片**硬链接**自 `/home/albus/strata166/weights/`（同一 FS => 零拷贝零额外空间，
  且删 `/weights` 后此份仍完整，链接数=2 已实测）；mmproj **真传输 907,543,008 B / 17.1 s / 52.6 MB/s**，
  两端 md5 均为 `f4a9346fb51f1d8521213c871578ca7c`；磁盘余量 251 GB 未变。
- **关键发现**：166 现役 `/weights` 的 3 分片与新下载**字节数完全一致**，且**抽样哈希（首/中/尾各 32 MB）逐一相同**
  （分片1 全量 md5 也相同 `cc6525294a5ce9e655ab370a72669a20`）=> **新下载与现役是同一份权重，唯一新增是 mmproj**。
  => 不必重传 94.6 GB。
- **未做（需机主裁定，因为会动正在服务的东西）**：
  1) 把 config 的 `--native` 从 `/weights/...` 改指 `/models/unsloth/...`（走 register 通道）+ 容器挂载相应调整；
     若要启用 vision，还需加 `--vision` + `vision` 段引用 mmproj（**现在图片输入仍是 400：without the vision encoder**）。
  2) **删 `/weights`（91.5 GB）必须在 1) 做完并复验之后就删**，否则下次重启找不到 native 会起不来。
  3) 本机 D: 上还有旧下载（`D:\\IDM\\Strata-UDIQ4XS\\` 93.7 GB、`D:\\IDM\\Strata-GGUF\\` 68 GB、`D:\\IDM\\Strata-UDQ4KXL\\` 111 GB 等）——
     **本机文件不自行动手**，等机主明确。
- **B3c（一致性判定）副产物**：见下面 W713j 段 ---- 它证明"贪心=可重复"在本机不成立，从而**回溯削弱** B1b 的"答案会变"与 B3b 的"互换"两条结论。
"""
io.open(log, "a", encoding="utf-8", newline="\n").write(note)
print("日志已追加", len(note))
