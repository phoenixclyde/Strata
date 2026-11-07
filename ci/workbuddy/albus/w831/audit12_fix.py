# -*- coding: utf-8 -*-
"""AUDIT12 就地修复：先 dry-run 校验锚点唯一性，全部命中才写入。"""
import io, sys

DEP = "D:/workbuddy_space/strata_ws/deploy/"
DRY = "--apply" not in sys.argv

PATCHES = {
 "W828_UPSTREAM_028_PORT.md": [
  # 1) decode 中位数算错
  ("**45.74 tok/s**（40.2 / 46.9 / 44.4 / 45.7 / 48.6） | **−0.35%**（噪声内）",
   "**45.70 tok/s**（40.2 / 46.9 / 44.4 / 45.7 / 48.6；中位 45.70、均值 45.16） | **−0.44%**（噪声内）"),
  # 2) 结论收窄（rocBLAS 污染）
  ("- 结论：**升级本身 0 回归、0 收益**，与 §2 的源码结论一致。",
   "- 结论（**AUDIT12 已收窄**）：**decode 0 回归、0 收益**；但 **read 三档不可比** ——\n"
   "  两臂代码不同源：`strata-0.1.54n` 里 `rocblas` 字符串 **0 个**（0.1.53 为 3 个，`build-028.log` 有 2 条\n"
   "  `rocblas_state_ ... not used`），而 rocBLAS 正打在 prefill 的 f16 GEMM 上（W830 §6 同镜像 A/B：常数项 1190→915 ms）。\n"
   "  所以 read 的 −6.2/+3.7/+9.8% 混了\"缺 W793\"这一项，不能拿来判引擎版本。"),
  # 3) §6.8 标题的 15 项
  ("### 6.8 AMD 开关全空间审计：上游给集显开的 15 项 exact 优化，我们一项都没开",
   "### 6.8 AMD 开关全空间审计：上游给集显开的 19 项 exact 优化，我们只手动开了 2 项（AUDIT12 更正）"),
  # 4) §6.8 正文 15 项
  ('`src/core/arch_defaults.cpp` 里 gfx1151 的 **15 项 "Exact (bitwise) on Aurora"** 优化',
   '`src/core/arch_defaults.cpp` 里 gfx1151 的 **19 项**（`arch_defaults.cpp:58-90` 逐条数得；原文写 15 项，AUDIT12 更正）'
   ' "Exact (bitwise) on Aurora" 优化'),
  # 5) §6.10 8 项 -> 5 项
  ('记了十几轮的"8 个会改 bits 的开关叠在一起值多少 KL"，这次量了。',
   '记了十几轮的"8 个会改 bits 的开关叠在一起值多少 KL"，这次量了其中 **5 个**\n'
   '（AUDIT12：账本 8 项里 `MMQ_KQ` 保留、`GDN_HEAD`/`GDN_PP` 根本没进表，实测只翻了 KV / RT_SKIP / PROMPT_F16 / SELECT_SIMT / HC_Q8）。'),
  # 6) §6.10 结论句 8 项
  ("我们 8 项叠加是它的 **5–10 倍**，量级自洽（8 项 ≠ 1 项）",
   "我们这 **5 项**叠加是它的 **5–10 倍**，量级自洽"),
  # 7) §6.12 反向句
  ('这一条同时解释了 §6.8 的全部结果：**没有任何单项能到 5%，所以每一项"省算力/省 launch"的开关都只值 ±1.5%。**',
   '这一条同时解释了 §6.8 的全部结果：**表里 >5% 的五项（专家读取 23.4% / 超连接 16.6% / GDN 15.6% / 等待 14.5% / QSA 13.1%）'
   '没有一项能靠单个开关整块拿掉**（每项本身又摊在多个 kernel 上），所以每一项"省算力/省 launch"的开关都只值 ±1.5%。'),
  # 8) §6.14 层数
  ("- 每窗口专家读取量 ≈ 21.4/层 × 60 层 × ~3.1 MB ≈ **3.9 GB**；对应 `VRAM hits` 的 10.51 ms ⇒ **约 375–400 GB/s**",
   "- 每窗口专家读取量 ≈ 21.4/层 × **48 层** × ~3.1 MB ≈ **3.2 GB**；对应 `VRAM hits` 的 10.51 ms ⇒ **约 300 GB/s（MI50 峰值的 ~30%）**\n"
   "  （AUDIT12 更正：模型是 **48 层**，`native_experts.txt` 的 layer 0..47 + `48×512=24576` 与 W829 §0 的 24576 实例一致；原写 60 层/3.9 GB/375–400 GB/s）"),
  # 9) §6.15 并集字节
  ('- 若它是"把 chunk 的专家并集从主机搬到 VRAM"：并集 ≈ 512 专家 × 60 层 × 3.07 MB ≈ **94 GB**，',
   '- 若它是"把 chunk 的专家并集从主机搬到 VRAM"：并集 ≈ 512 专家 × **48 层** × 3.07 MB ≈ **75 GB**（AUDIT12 更正：原按 60 层写 94 GB），'),
  # 10) §6.16 搬运账
  ("1. `=0` 的固定项确实是 **PCIe 搬运**：并集 94 GB − 缓存 21.8 GiB ≈ 72 GB，`72/4.74 ≈ 15 GB/s`",
   "1. `=0` 的固定项确实是 **PCIe 搬运**：并集 **75 GB** − 缓存 21.8 GiB(=23.4 GB) ≈ **52 GB**，`52/4.74 ≈ 11 GB/s`\n"
   "   （AUDIT12 更正：原用 60 层得 72 GB / 15 GB/s —— 15 GB/s 已超过 PCIe 3.0 x16 的实际带宽上限，"
   "与 W829 §0 的 \"~12 GB/s 实测\" 自相矛盾；48 层下 11 GB/s 反而对得上）"),
 ],

 "W829_OPT_PLAN.md": [
  ("| `--batch 2`（窄版，窗口 4 行足够） | 第 2 个 slot 的 KV ≈ 214 MiB（k8v4 × 256K）⇒ 槽位 −71（−0.9%） | 单流延迟不回归 + 双流合计 tok/s |",
   "| `--batch 2`（窄版，窗口 4 行足够） | 第 2 个 slot 的 KV ≈ **2.95 GiB**（k8v4 × 256K，引擎日志实测；原文 214 MiB 是 32K 的口径，差 14 倍 —— AUDIT12 更正）⇒ 槽位 **−2016（−27%）** | 单流延迟不回归 + 双流合计 tok/s |"),
  ("| `--batch 4` | KV 856 MiB ⇒ 槽位 −285（−3.8%） | 同上 |",
   "| `--batch 4` | KV ≈ 11.8 GiB（4×2.95）⇒ 槽位 −4000 量级（**原文 856 MiB/−285 已作废**） | 同上 |"),
  ("| `--batch 9..16`（**只有宽版能跑**） | KV 1.9-3.4 GiB ⇒ 槽位 −9~15% | 只有真需要 9+ 并发才做 |",
   "| `--batch 9..16`（**只有宽版能跑**） | KV ≈ **26.6–47.2 GiB ⇒ 装不下**（W828 §6.4 实测：16 slots 需 47 GiB，8 slots 已 OOM；原文 1.9-3.4 GiB 作废） | 只有真需要 9+ 并发才做 |"),
  ("| 时间构成 | decode 占一轮 **64-83%**；prefill 内部 gate/up 22.7% / down 14.7% / attn 12.0% / gdn 11.8% |",
   "| 时间构成 | decode 占一轮 **64-83%**；prefill 内部 gate/up 22.7% / down 14.7% / attn 12.0% / gdn 11.8%（**合计仅 61.2%**，余 38.8% 见 W825 原表 —— AUDIT12） |"),
  ('8. **数值债结清了**（P193）：8 个"会改 bits"的开关叠加',
   '8. **数值债部分结清**（P193，AUDIT12 收窄）：账本 8 项里实测只翻了 5 项（`MMQ_KQ` 保留、`GDN_HEAD`/`GDN_PP` 未动），所以下面这个数是 **5 项**的总账'),
 ],

 "W830_PATCH_LOSS_INCIDENT.md": [
  ("| `serve/web/app.js` 的 **WEB-UI**（API key 本地存、分页、轴下限） | 没丢 | 树与镜像里 `saveApiKey`/`tab-btn-images` 都在 |",
   "| `serve/web/app.js` 的 **WEB-UI** | **丢了 4 行，已由 W831 补回** | 部署的 `app.js` 与上游 v0.2.8 **字节相同**（md5 `9fed14d1…`）；"
   "`saveApiKey`/`tab-btn-images` 是**上游自带**的词，当时据此判\"没丢\"是**假绿**（AUDIT12 更正）。真缺的是 PCIe 卡的 `· peak NN MB/s` |"),
  ("> 一句话结论：**丢了两处代码补丁 + 一处 serve 补丁；已全部找回",
   "> 一句话结论：**丢了两处代码补丁 + 一处 serve 补丁 + 一处 Web 补丁的 4 行；已全部找回"),
  ("| 验证 | `/metrics` 出现 `gpu_pcie_rx_mb: 60.65`；decode **46.27 tok/s**（修复前 46.25/46.28，无回归）；TTFT 常数项 **1206 → 843 ms**（边际不变 1.317→1.328，见 §6 的 A/B） |",
   "| 验证 | `/metrics` 出现 `gpu_pcie_rx_mb: 60.65`；decode **46.27 tok/s**（修复前 46.25/46.28，无回归）；TTFT 常数项以 §6 的 **1190 → 915 ms**（ABBA 各两轮）为准 —— 本节原写的 1206→843 是**单次复核读数**，不作结论（AUDIT12 更正） |"),
  ("`CMakeLists.txt`（3 处标记 → 现在 0 处）和 `qsa_decode_attn.cu`（W794，在）。",
   "`CMakeLists.txt`（3 处标记；**发现时 0 处、恢复后 2 处** —— AUDIT12 更正）和 `qsa_decode_attn.cu`（W794，在）。"),
  ("| 我们自加的 2824 个本地文件（third_party、构建等） | 一个没丢 | src028 里全部存在 |",
   "| 我们自加的约 2800 个本地文件（third_party 等） | 一个没丢 | `third_party` 实测 2832 个文件；按 7973−5205 / 8002−5229 算是 2768/2773，原文 2824 无法精确复现（AUDIT12） |"),
  ("`albus/w830/verify_patches.sh` —— 升级/重编/换镜像后必跑，8 项检查",
   "`albus/w830/verify_patches.sh` —— 升级/重编/换镜像后必跑，**现行 13 项检查**（写此文时 8 项，W831 后扩到 13）"),
 ],
}

ok = True
for fn, reps in PATCHES.items():
    p = DEP + fn
    s = io.open(p, encoding="utf-8").read()
    print("==", fn, "len", len(s))
    for old, new in reps:
        c = s.count(old)
        flag = "OK " if c == 1 else "!! "
        if c != 1:
            ok = False
        print("   %s hits=%d  %s" % (flag, c, old[:64].replace("\n", " ")))
        if c == 1:
            s = s.replace(old, new, 1)
    if not DRY and ok:
        io.open(p, "w", encoding="utf-8", newline="\n").write(s)
        print("   written", len(s))

print("\nALL_ANCHORS_OK" if ok else "\nSOME_ANCHORS_MISSING")
print("DRY_RUN" if DRY else "APPLIED")
