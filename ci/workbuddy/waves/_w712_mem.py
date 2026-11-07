# 写记忆：今日日志追加 W712 段；并把 MEMORY.md 的"现役"行改成 0.1.40.4 / strata166-404
import io, os

day = r"D:/workbuddy_space/strata_ws/.workbuddy/memory/2026-10-08.md"
mem = r"D:/workbuddy_space/strata_ws/.workbuddy/memory/MEMORY.md"

note = """
## W712 升级波（2026-10-08 20:0x-20:4x，接手会话）
机主令：「今天 strata 又有新版发布了。你先升级到最新版。你还是拉近几版的更新情况，在昨天的基础上（包括待办和已办）给一个方案。」
- 上游：`v0.1.40.4`（10-08 08:04 UTC）；此前 `0.1.40.3`（10-07 18:01）。0.1.40.3 = Intel Arc/Windows AMD 热修，0.1.40.4 = Pascal sm_61 解码热修。
- 全树逐文件比对（pristine zip 对 pristine zip）：2,260 -> 2,262 文件；34 改 + 2 增（tools/hip/dll_closure.py 等，Windows 用）。
  与我们相关的三处均已逐条判过（pdl.hpp 的 HIP 分支一字未动、native_bf16/native_mmvq 的 __restrict__ 挪进函数体、mtp.cpp 的 512 专家门对本机恒成立）。
- **补丁面与 0.1.40.2 完全相同**：H1~H4 上游已修（验证）、H5+H6 仍需打；`patch_gfx906_402.py`(v3) 一字未改，
  dry-run on 0.1.40.4 = patched=2 / verified=4 / failed=0，第二遍 patched=0（幂等）。`LLAMA_CPP_COMMIT` 未变 => llama.cpp 复用。
- 源码 sha256 `7d19b4d5cc8922d4e558f2cddec9a28b7595775ccfb4e6085b02287d95059300`（本机与 166 **各自下载、哈希相同**）。
- 新镜像 `strata-gfx906:0.1.40.4`（`8f8f6e87e664` / 6.57 GB）；引擎 `/src/build-906/strata` = 24,841,832 B / md5 `b0020081b8292d48c4a555c5f036081b`。
- **已切换**：20:11:47 停 `-402` -> 20:11:52 起 `strata166-404` -> 20:12:28 ready（**35 s**）；脚本自带 300 s 轮询 + 自动回滚（rc=0）。
  复验 `verify_config.py` **PASS=15 / FAIL=0**；LIVE md5 未变 `d2b10f0c4e8293ba010614c7acc70bea`；**本波未改任何参数**（register md5 仍 `a91b677ea13905cb36ef56fa6224c36d`）。
- **中性验证（背靠背 A/B，实测）**：冷预填 **456.1 vs 457.6 tok/s（-0.33%）**、温 TTFT **5.753 vs 5.853 s**、
  `reused` **均 16384**、常驻专家 RAM 均 33.45 GiB => 落在分辨力（预填 1.2-1.7%）内，**两版不可分辨**。
  注意：本次生成只有 32 token，**不是解码基准**，0.1.40.4 解码分母仍缺（A2）。
- 事故与修复（自报）：把含反引号的文本经 Bash + python -c 传递 => shell 先做命令替换，`workbuddy-strata166.md` 追加的 §九 被抓空，已重写；
  同时清掉该文件**存量**禁用码位 14 处（只动标点）；新 Dockerfile 注释 5 处禁用码位已清并重推 166（两侧 md5 相等，diff 证明只动 3 行注释）。
  存量未清（报出不动）：`Dockerfile-0.1.40.2` 6 处、`patch_gfx906_402.py` 14 处（是本次构建输入件）。
- 交付件：`deploy/W712_UPGRADE.md`（升级记录与自证）、`deploy/W712_PLAN.md`（方案）；`PROJECT.md`/配置件的现役项已更新为 0.1.40.4 / strata166-404。
"""

with io.open(day, "a", encoding="utf-8", newline="\n") as f:
    f.write(note)
print("appended to", os.path.basename(day), len(note), "chars")

t = io.open(mem, encoding="utf-8").read()
old = "现役：镜像 `strata-gfx906:0.1.40.2` / 容器 `strata166-402` / 端口 8090"
new = "现役：镜像 `strata-gfx906:0.1.40.4` / 容器 `strata166-404` / 端口 8090"
assert old in t, "anchor not found in MEMORY.md"
t2 = t.replace(old, new)
old2 = "- P34 补 `>16k` / `<8k` 两档。"
add2 = "- P34 补 `>16k` / `<8k` 两档；**0.1.40.4 解码基准重测（A2）**。"
if old2 in t2:
    t2 = t2.replace(old2, add2)
io.open(mem, "w", encoding="utf-8", newline="\n").write(t2)
print("MEMORY.md %d -> %d chars" % (len(t), len(t2)))
