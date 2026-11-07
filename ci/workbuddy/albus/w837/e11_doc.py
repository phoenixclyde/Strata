import io

p = 'D:/workbuddy_space/strata_ws/deploy/W836_BRANCH.md'
s = io.open(p, encoding='utf-8').read()

s = s.replace('| head | **`923c2118`**（2026-10-31，**7 个 commit**） |',
              '| head | **`642de24f`**（2026-10-31，**8 个 commit**） |')
s = s.replace('| 相对上游 | **ahead 7 / behind 0** |', '| 相对上游 | **ahead 8 / behind 0** |')
s = s.replace('| 改动面 | **6 个文件，+94 / −7** |', '| 改动面 | **10 个文件，+216 / −9** |')
s = s.replace('| 166 工作副本 | `/home/albus/strata166/gfx906`（depth-1 clone，5319 文件，已跟到 `923c211`） |',
              '| 166 工作副本 | `/home/albus/strata166/gfx906`（depth-1 clone，5319 文件，已跟到 `642de24`） |')

s = s.replace('| 7 | `923c2118` | `include/strata/platform/hip_compat/strata_hip.h` | +4 | **W830-COMPAT** stream priority 两个宏 |',
              '| 7 | `923c2118` | `include/strata/platform/hip_compat/strata_hip.h` | +4 | **W830-COMPAT** stream priority 两个宏 |\n'
              '| 8 | `642de24f` | `gfx_arch.hpp` / `arch_defaults.hpp` / `arch_defaults.cpp` / `arch_defaults_test.cpp` | +122/−2 | **gfx906 架构入口**（谓词 + 精确表 + opt-in 配方），见 §10 |')

s = s.rstrip('\n') + '''

---

## 10 第 8 个 commit：给 gfx906 一个架构入口

### 10.1 改之前的状态

`arch_default_env()` 在 `if (!gfx_arch_is_gfx1151) return t;` 处返回空表，`gfx_arch.hpp` 只有 4 个谓词
（gfx11_wmma / gfx12 / gfx12_wmma / gfx1151），**没有 gfx906**。gfx906 只在各 kernel 里靠字符串认身份。

后果最直接的是这两个开关——**它们是为 gfx906 写的，却默认关闭**：

| 开关 | 读取点 | unset 时 |
|---|---|---|
| `STRATA_GFX906_ATTN_REDUCE12` | `qsa_decode_attn.cu:997` | **off** |
| `STRATA_GFX906_ATTN_QUERY_SWIZZLE` | `qsa_decode_attn.cu:967` | **off** |

也就是说：不知道这两个名字的 gfx906 用户，两个专用 kernel 一个都用不上。

### 10.2 改了什么（按上游的既有规矩分两层）

上游 `arch_defaults.hpp` 的原则写得很明确：**表里默认开的必须实测且位等价；改 bit 的保持 opt-in**。
所以没有把生产的 14 个 env 一股脑塞进去，而是照 gfx1151 的做法分两层：

**① 精确表 `arch_default_env("gfx906")` —— 2 项，都有位等价实测**

| 开关 | 位等价证据 |
|---|---|
| `STRATA_GDN_HEAD=1` | teacher-forced LOGPOS：KL mean **0.0000**、median 0、argmax **100%**、top-10 **1.00**、mean\\|Δlp\\| **0.00000** |
| `STRATA_GFX906_ATTN_REDUCE12=1` | 同一批 prompt 的三份 LOGPOS dump **md5 完全相同**（开关开/关/再开） |

关掉：`STRATA_GFX906_DEFAULTS=0`；`STRATA_DEFAULTS=026` 时返回空（0.2.6 没有 gfx906 表可还原）。

**② opt-in 配方 `gfx906_tuned_env()` —— 7 项，`STRATA_GFX906_TUNED=1`**

| 开关 | 值 | 位代价（同引擎 teacher-forced） |
|---|---|---|
| `STRATA_GFX906_ATTN_QUERY_SWIZZLE` | 1 | 未做 md5 门（生产在用） |
| `STRATA_GDN_PP` | 2 | 未单独门（gfx1151 表第二项） |
| `STRATA_HC_Q8` | 1 | KL 0.0011，argmax 100% |
| `STRATA_SELECT_SIMT` | 1 | KL 0.0004，argmax 100% |
| `STRATA_ROUTE_TAIL_SKIP` | 7 | KL 0.0008，argmax 100% |
| `STRATA_MMQ_KQ` | 1 | KL 0.0171，argmax 100%，**+68% prompt** |
| `STRATA_HIP_PROMPT_F16` | 1 | KL 0.0026，约 1.6× prompt |

**注释里明写"这些 KL 不相加"**：五项同关的总量 0.0293，而逐项和只有 0.0062（P215）。

**③ `gfx_arch_is_gfx906()`** 谓词，与前四个并列。

### 10.3 验证（不用等 40 分钟全量构建）

`arch_defaults_test` 只链接 `arch_defaults.cpp`，可以单独编译：

```
g++ -std=c++17 -I include -o /tmp/adt src/core/arch_defaults_test.cpp src/core/arch_defaults.cpp
```

| 检查 | 结果 |
|---|---|
| 编译 | ✅ rc=0 |
| 原有用例（gfx1151 18 项 / gfx12 9 项 / igpu 集） | ✅ 全部仍然通过 —— **没有改动任何现有架构的行为** |
| gfx906 新用例 | ✅ 表恰好 2 项、精确表里"不含任何改 bit 的开关"、`defaults026` 返回空、`DEFAULTS=0` 返回空、tuned 仅 gfx906 且需 `TUNED=1`、`gfx9060` 不误匹配、`gfx906:sramecc-:xnack-` 后缀可用 |
| 运行时 banner | ✅ `strata: gfx906 (MI50-class): 2 exact speed switches on by default (STRATA_GFX906_DEFAULTS=0 turns them off; a switch you set is kept): GDN_HEAD GFX906_ATTN_REDUCE12` |
| 用户设置优先 | ✅ 预先设 `GDN_HEAD=0` 后再 apply，`set 0` 且值保持 0 |

### 10.4 已同步到构建树，但**还没重编**

`sync_gfx906.sh` 已把这 4 个文件同步进 `src028`，**补丁门禁 11 项全 OK**。
生产二进制仍是 `strata-0.1.54n2`（不含本改动）；下次重编才会生效。

**重编后行为应当完全不变**：生产启动脚本已经手工设了这 9 项（2 + 7），而 `apply_arch_defaults` 只设
"用户没设过的"变量 ⇒ 两边取值一致，不产生新的差异。

### 10.5 同步脚本的一处必要修正

原来 `FILES` 里含 `CMakeLists.txt`，会**整文件覆盖**——那会把上游 main 的 29 行改动拖进 `src028`（v0.2.8 基底）。
已改为：**CMakeLists 只检查补丁标记（`W793` / `W776 local`），不做文件复制**。
'''
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('W836_BRANCH.md updated, len', len(s))
print([l for l in s.split('\n') if l.startswith('## ')][-3:])
