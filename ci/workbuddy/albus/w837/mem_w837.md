## W837　给 gfx906 加架构入口（2026-10-31 16:17–16:3x）

- **改前状态**：`arch_default_env()` 在 `if (!gfx_arch_is_gfx1151) return t;` 处返回空表；`gfx_arch.hpp` 只有
  4 个谓词（gfx11_wmma / gfx12 / gfx12_wmma / gfx1151），**没有 gfx906**。最直接的后果：
  `STRATA_GFX906_ATTN_REDUCE12`(`qsa_decode_attn.cu:997`) 与 `STRATA_GFX906_ATTN_QUERY_SWIZZLE`(`:967`)
  ——**两个专为 gfx906 写的开关，unset 时都是 off**，不知道名字的用户一个都用不上。
- **改法（按上游既有规矩分两层，不把 14 个 env 一股脑塞进去）**：
  - **精确表 2 项**（位等价才默认开）：`STRATA_GDN_HEAD=1`（LOGPOS KL **0.0000** / argmax 100% / top10 1.00 /
    mean|dlp| 0.00000）、`STRATA_GFX906_ATTN_REDUCE12=1`（三份 LOGPOS dump **md5 完全相同**）。
    `STRATA_GFX906_DEFAULTS=0` 可关；`STRATA_DEFAULTS=026` 返回空（0.2.6 无此表）。
  - **opt-in 配方 7 项**（`STRATA_GFX906_TUNED=1`）：QUERY_SWIZZLE 1 / GDN_PP 2 / HC_Q8 1(KL .0011) /
    SELECT_SIMT 1(.0004) / ROUTE_TAIL_SKIP 7(.0008) / MMQ_KQ 1(.0171 且 +68% prompt) / HIP_PROMPT_F16 1(.0026 约 1.6x)。
    注释明写**这些 KL 不相加**（五项同关 0.0293 vs 逐项和 0.0062，P215）。
  - `gfx_arch_is_gfx906()` 谓词，与前四个并列。
- **快速验证路线（关键）**：`arch_defaults_test` 只链接 `arch_defaults.cpp`，可**单独 g++ 编译**，不用等 40 分钟全量构建。
  结果：编译 rc=0，**全绿**；gfx1151 18 项 / gfx12 9 项 / igpu 断言**全部未变**（没动任何现有架构）；
  新增 gfx906 用例覆盖「精确表内不含任何改 bit 的开关」「`gfx9060` 不误匹配」「`gfx906:sramecc-:xnack-` 后缀可用」
  「DEFAULTS=0 / defaults026 返回空」「tuned 仅 gfx906 且需 TUNED=1」。
  运行时 banner 正确：`strata: gfx906 (MI50-class): 2 exact speed switches on by default ...: GDN_HEAD GFX906_ATTN_REDUCE12`；
  预置 `GDN_HEAD=0` 后再 apply 得 `set 0` 且值保持 0（用户优先）。
- **已入分支**：第 8 个 commit **`642de24f`**，10 文件 +216/−9，head 前进；**ahead 8 / behind 0**。
  `sync_gfx906.sh` 已把 4 个新文件同步进 `src028`，**补丁门禁 11 项 OK**。
- **生产未重编**：二进制仍是 `strata-0.1.54n2`（不含本改动）。**重编后行为应完全不变**——生产脚本已手工设这 9 项，
  而 `apply_arch_defaults` 只设"用户没设过的"，两边取值一致。
- **顺带修 sync 脚本的隐患**：`CMakeLists.txt` 不再整文件覆盖（那会把上游 main 的 29 行拖进 v0.2.8 基底），
  改为只检查 `W793` / `W776 local` 两个标记。
- 文档 `deploy/W836_BRANCH.md` §10；登记 **P224（ADOPTED）**，221 行。
