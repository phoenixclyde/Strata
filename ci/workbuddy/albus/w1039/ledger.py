import io

P = "deploy/PROGRESS.tsv"

ROWS = [
    dict(
        block="B4上游移植", id="P445",
        item=("pa3 建成：port-all 按 b12180 的 llama 树重编（换 /llama.cpp + 重 configure），"
              "clean rebuild 与增量件**位相同** md5 `b2ba6304…` ⇒ 可复现"),
        source="W1039", kind="count", count="1", done="1", status="DONE",
        note=("**W1039（机主 08:51「正确顺序：按 b12180 配方重编 port-all … → 得到 pa3」）**。"
              "配方：`/src`=pr/port-all、`/out`=build-pa3（**从 build-port2 整目录拷来**以继承全部 cmake flags）、"
              "`/llama.cpp`=tmp/w1037/llama-master（就是 b12180 用的那棵树，mmq.cuh `627c4c62`）。"
              "**踩到两条必须记的**：① port-all 的 `cmake/strata_ggml_tq_overlay.cmake` 还是旧探测（按 `get_nthreads` 推断第 5 个模板实参），"
              "对 b12180 必挂 ⇒ 把 pr/k10 的 W1037 修（直接探 write-back 自己的签名）搬过去；"
              "② 光换树不够，**还要补 b12110 的 API 差**：`mul_mat_q_case` 加 `GGML_PREC_Q8`（26 处，含 port-all 独有的 `mmq_nvfp4_w4a4.cu`）、"
              "`ggml_cuda_mmq_get_config` 加精度参（5 处）、`new_pool_for_device` 加 ctx 形参（1 处）。"
              "**可复现性验证**：把 build-pa3 再拷一份、`ninja -t clean` 后全量重编，得到**同一个 md5 `b2ba6304ddc848100ba72140e49ef9a9` / 43,306,640 B** ⇒ "
              "既证明没有残留旧树目标文件，也证明该件可由配方重建（REBUILD_RECIPE 已登记）。"
              "本件重启 0 次、停机 0（只编译，未装机）。"),
        ref="P441;P433", kw="KW:pa3|可复现"),
    dict(
        block="B6判定探针", id="P446",
        item=("窗口1 三臂零效果的真因：生产开着 `GFX906_ATTN_QUERY_SWIZZLE`（`STRATA_GFX906_TUNED=1` 的配方），"
              "而 W1037 接的 OPT 分支被 `!use_query_swizzle` 挡掉 ⇒ 又是一次「改到死代码」"),
        source="W1039", kind="count", count="1", done="1", status="DONE",
        note=("**W1039 实测（pa3 窗口，重启 3 次、停机 129 s）**：ctl(b12180) / pa3+ATTN_DP4A / pa3+DPP+LDS_PAD+ROUTE_DPP，"
              "每臂 2.5K×2+8K×2+16K×2。结果 `qsa attn` 8K **2238 → 2235 / 2232 ms**、16K **4731 → 4718 / 4750 ms**，整条 prefill 偏差 ≤0.15%（2×CV 0.19%）⇒ 逐毫秒不动。"
              "**根因（源码 + 启动横幅互证）**：引擎日志 `:146006` 的横幅写着 *\"the rounding-level recipe is on … GFX906_ATTN_QUERY_SWIZZLE GDN_PP HC_Q8 SELECT_SIMT ROUTE_TAIL_SKIP HIP_PROMPT_F16\"* ⇒ "
              "`use_query_swizzle` 为真；而 `launch_chunks_batch` 里 W1037 那段的条件是 `opt != 0 && !lane_cell && !use_query_swizzle` ⇒ 永远不成立。"
              "生产实际跑的是 `attn_chunk_kernel<3,false,true,true>`（swizzle+reduce12），OPT 版本是 `<M,false,false,false,OPT>`，两者不是同一条实例化。"
              "**教训（与 `P425`/`P441` 同族，第三次）**：判断「开关在不在热路径」不能只看函数名被谁调，"
              "还要看**生产配方把哪些模板实例化打开着**——`STRATA_GFX906_TUNED=1` 本身就是一组开关。"),
        ref="P441;P425", kw="KW:QUERY_SWIZZLE|死代码"),
    dict(
        block="B6判定探针", id="P447",
        item=("pa4（OPT 接进 swizzle 分支）实测：**DP4A 让 attn 慢 6.8%/7.35%**、整条 prefill +1.07%/+1.44%；"
              "DPP 使 attn −0.76%/−0.47%、整条 +0.10%/+0.14% ⇒ B1/B2 两支均 DONE_NEG"),
        source="W1039", kind="count", count="1", done="1", status="DONE_NEG",
        note=("**W1039 第二窗口（重启 3 次、停机 135 s；两窗口合计重启 6 次、停机 264 s）**。pa4 把 OPT 派发放进 `if (use_query_swizzle)` 内，"
              "用 `attn_chunk_kernel<M,false,true,true,O>`（保留生产用的 swizzle+reduce12，只换内层）。"
              "**这次开关确实在跑**——证据是 attn 相位动了，而且方向是**变慢**："
              "8K `qsa attn` 2234 → **2387 ms（+6.84%）**、16K 4727 → **5074 ms（+7.35%）**；整条 prefill 8K +1.07%（2×CV 0.10%）、16K +1.44%（2×CV 0.51%）⇒ **显著负收益**。"
              "DPP：8K attn 2234 → 2217（−0.76%）、16K 4727 → 4705（−0.47%），整条 +0.10%/+0.14%（2×CV 0.86%/0.13%）⇒ 中性偏负。decode 三臂 62.35 / 62.42 / 60.75 tok/s（CV 7–10%）⇒ 不可分。"
              "**机制解释（推测，未单独测）**：dp4a 分支每题要把 q 量化成 int8 + 每 64 值一个 scale（`sq8`/`sq8s`，`qsa_decode_attn.cu:199-200`），"
              "并把 `SQ_HEADS` 从 G 降到 1（换掉原来的 fp32 共享 tile）⇒ 量化与 LDS 搬运的开销超过 dot 指令省下的；"
              "而 V 累加仍是 fp32 `fmaf`，没被 dp4a 覆盖。**要证实需在 pa4 上加一次性计数或 profiler，不在本轮范围**。"
              "**判决：B1(DPP)/B2(DP4A) 在 gfx906 生产配置上都不采用**；R103 的 attn 一支就此收口，剩余子项转向 A1/A5。"),
        ref="P446", kw="KW:DP4A|DONE_NEG"),
    dict(
        block="B6判定探针", id="P448",
        item=("修掉一个静默正确性洞：`STRATA_ATTN_OPT_DISPATCH` 只有 case 1/2/4，"
              "opt=5（DPP|LDS_PAD）时落 `default: break;` 后直接 `return` ⇒ **一个内核都不发、也不报错**"),
        source="W1039", kind="count", count="1", done="1", status="DONE",
        note=("**W1039 发现并修**。W1036 写这份派发时按「单开关」设计：`switch (opt) { case 1 / case 2 / case 4 }`，"
              "`default: break;` 之后紧接着 `return;`（`qsa_decode_attn.cu:1077-1084` 与 W1037 新加的分支）。"
              "后果：只要同时开两个开关（例如 `ATTN_DPP=1` + `ATTN_LDS_PAD=1`，opt=5），函数会**一个 kernel 都不启动就返回**，"
              "调用方照常做 merge ⇒ 输出是上一轮的残留/未初始化数据，**看起来只是答案变差，不会报错**。"
              "本轮 `P446` 的第一窗口恰好因为 swizzle 挡住没走到这里，否则 c 臂测到的会是「零成本」的假象。"
              "修法：两组派发宏都扩到 `case 1..7`（3 个 bit 的全部组合），pa4 已含。"),
        ref="P441", kw="KW:组合|静默"),
]

s = io.open(P, encoding="utf-8").read()
add = []
for r in ROWS:
    if ("\t" + r["id"] + "\t") in s:
        print("skip", r["id"])
        continue
    add.append("\t".join([r["block"], r["id"], r["item"], r["source"], r["kind"], r["count"], r["done"],
                          r["status"], r["note"], r["ref"], r["kw"]]))
if add:
    if not s.endswith("\n"):
        s += "\n"
    s += "\n".join(add) + "\n"
    io.open(P, "w", encoding="utf-8", newline="\n").write(s)
    print("appended", len(add), [a.split("\t")[1] for a in add])

# rebuild recipe rows
R = "deploy/REBUILD_RECIPE.tsv"
t = io.open(R, encoding="utf-8").read()
ROWS2 = [
    ("strata-0.1.57-pa3", "b2ba6304ddc848100ba72140e49ef9a9", "43306640",
     "gfx906/port-all @ 8b5e547f", "b12180 / bcb0152876e8f0b684ba70d3defcab6cdf35adb5",
     "4c1004c49221b07c3b8108977e3d1991fc9f45cc", "build-pa3（/src=pr/port-all，/llama.cpp=tmp/w1037/llama-master）",
     "W1039 候选；clean rebuild 位相同，见 P445"),
    ("strata-0.1.57-pa4", "49937458627b0a40038e237cae352a06", "43569792",
     "gfx906/port-all @ 8b5e547f（+pa4 未提交补丁）", "b12180 / bcb0152876e8f0b684ba70d3defcab6cdf35adb5",
     "4c1004c49221b07c3b8108977e3d1991fc9f45cc", "build-pa3（同上，增量）",
     "W1039 候选：OPT 派发搬进 swizzle 分支；**未提交**，见 P447/P448；A/B 窗口内临时装机后已还原"),
]
lines = []
for exe, md5, size, sha, base, mmq, bd, note in ROWS2:
    if exe + "\t" in t:
        print("recipe skip", exe)
        continue
    lines.append("\t".join([exe, md5, size, sha, base, mmq, bd, note]))
if lines:
    if not t.endswith("\n"):
        t += "\n"
    t += "\n".join(lines) + "\n"
    io.open(R, "w", encoding="utf-8", newline="\n").write(t)
    print("recipe rows +", len(lines))
