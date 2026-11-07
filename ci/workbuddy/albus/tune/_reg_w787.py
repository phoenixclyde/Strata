# -*- coding: utf-8 -*-
"""W787：P93 判 REJECTED（R1 修的是不存在的问题）+ 新增 P94（真实多轮复用基线）。"""
import io, shutil, time

REG = r"D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv"
shutil.copy2(REG, REG + ".bak_w787_" + time.strftime("%Y%m%d_%H%M%S"))

P94 = "\t".join([
    "P94", "REF", "真实多轮复用基线", "7.3K ctx", "prefill", "REFERENCE", "-", "-", "-",
    "【W787 实测 2026-10-25 05:3x，0.2.4/0.1.49.2 无补丁】真实对话形态（messages 数组，ctx 只在第 1 轮出现，后续只发新问题）："
    "turn1 prompt 7,349 / read 7,349 / reused 0 / prompt_ms 15,330 / wall 16.7s；"
    "turn2 prompt 7,377 / read 33 / **reused 7,344** / prompt_ms **685** / wall 1.7s；"
    "turn3 prompt 7,393 / read 21 / **reused 7,372** / prompt_ms **558** / wall 1.5s。"
    "=> 8K 以下的真实多轮**本来就复用**，且第 2 轮起 prefill 从 15.3s 降到 0.69s（22 倍）、0.56s（27 倍）。"
    "=> 同时纠正 W786 §1 的适用边界：单轮时长文档 prefill 占 57-99.5%；多轮追问复用后 prefill 仅 0.6s 量级，"
    "decode 才是大头（320 token 输出时约 99%）。故 decode 侧各项在多轮场景的端到端占比就是其 ms/window 占比。"
    "三个错误的旧测法：w778_mt.py（三轮结尾不同=分支场景）、追加时加\"答N：\"标签（破坏前缀）、"
    "每轮 user 消息都含完整 ctx（prompt 翻倍绕过 8192）。",
    "取代 W781 §3 与 W786 §3 的「8K 以下零复用」结论"])

lines = io.open(REG, encoding="utf-8-sig").read().splitlines()
out, hit = [], False
for ln in lines:
    if ln.startswith("P93\t"):
        f = ln.split("\t")
        f[5] = "REJECTED"
        f[9] = ("【2026-10-25 05:4x W787 判 REJECTED】补丁已实现并上过生产（镜像 strata-gfx906:0.2.4r1，"
                "日志每请求 `1 checkpoints` 证明分支被走到），但**零收益**：三轮仍 `0 reused`。"
                "两层原因：① 存下的「整段长度」checkpoint 在 park 时被 `drop_superseded` 删掉"
                "（日志 `dropped 1 superseded copy`；源码 generate.cpp:9492 注释：出站链已覆盖它）；"
                "② 前提高估——真实多轮本来就能复用（见 P94，第 2 轮 reused 7,344、prompt_ms 685），"
                "「8K 以下零复用」是三个测试脚本构造错误的产物。生产已回滚到 0.2.4，r1 镜像与容器留档不用。")
        f[10] = "已废：修的是不存在的问题；见 P94 与 W787"
        ln = "\t".join(f)
        hit = True
    out.append(ln)
assert hit, "P93 not found"

out = [ln for ln in out if not ln.startswith("P94\t")]
out.append(P94)
io.open(REG, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
print("register updated, rows =", len(out))
