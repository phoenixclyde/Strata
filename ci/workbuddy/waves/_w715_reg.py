# W715：改 PARAM_REGISTER（切 huihui + 新增 vision 面条目）。先归档，再改，五断言自证
import io, os, re, shutil, time

REG = r"D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv"
BAK = REG + ".bak_w715_" + time.strftime("%Y%m%d_%H%M%S")
NEW_NATIVE = ("/models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/unsloth-UD-IQ4_XS/"
              "Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf")

raw0 = io.open(REG, encoding="utf-8").read()
n0 = len(raw0.splitlines())

# 1) 归档
shutil.copy2(REG, BAK)
assert io.open(BAK, encoding="utf-8").read() == raw0, "归档不一致"
print("归档 -> %s (%d B)" % (os.path.basename(BAK), os.path.getsize(BAK)))

lines = raw0.splitlines()
hdr = lines[0]
assert hdr.split("\t")[0] == "id", "表头异常"
ncol = len(hdr.split("\t"))
print("表头列数 =", ncol)

out, changed = [], []
for ln in lines[1:]:
    if not ln.strip():
        continue
    f = ln.split("\t")
    assert len(f) == ncol, "列数不符: %r" % ln[:70]
    rid = f[0]

    if rid == "P00":
        assert f[3] == "/data/packs/ud-iq4_xs", "P00 现值不符: %r" % f[3]
        f[3] = "/data/packs/huihui-ud-iq4_xs"
        f[9] = ("W715 切 abliterated：pack 由 huihui 分片1 重生成（tools/iq_pack.py --compat-bf16）；"
                "实测 dense.bin / index.txt / native_experts.txt / conversions.json 与 base pack 逐字节相同，"
                "仅 compat-bf16.json 差 4 行（源分片哈希）=> abliteration 的差异只落在 experts（--native 直读）")
        f[10] = "W715 切换（huihui abliterated）"
        changed.append("P00 --pack -> /data/packs/huihui-ud-iq4_xs")
    elif rid == "P01":
        assert "/models/unsloth/" in f[3], "P01 现值不符: %r" % f[3]
        f[3] = NEW_NATIVE
        f[9] = ("W715 切换：指向 huihui 分片1；引擎按名字在同目录找 00002/00003（huihui 实体），"
                "分片1 与 base 逐字节相同（5ce89370）故此处为软链；PLE 表（per_layer_token_embd.weight）在分片2")
        f[10] = "W715 切换（huihui abliterated）"
        changed.append("P01 --native -> huihui 分片1")
    elif rid == "P20":
        assert f[3] == "/data/profiles/ud-iq4_xs-learned.bin", "P20 现值不符: %r" % f[3]
        f[3] = "/data/profiles/huihui-ud-iq4_xs-learned.bin"
        f[9] = f[9] + "；W715：切 huihui 后另起文件名，避免覆盖 base 的学习结果"
        changed.append("P20 --expert-profile-save -> huihui-...-learned.bin")
    out.append(f)

# 2) 新增 vision 面条目（P99 CLI flag + V00-V02 config 段）
new_rows = [
    ["P99", "CLI", "--vision", "(flag)", "vision", "ADOPTED", "-", "-", "-",
     "W715 新启用：strata-vision 由 tools/vision 编译（cmake -S tools/vision -B /data/vision-build -G Ninja "
     "-DCMAKE_BUILD_TYPE=Release -DLLAMA_DIR=third_party/llama.cpp；PORTABLE=ON/AVX2 基线，本机 Xeon E5-2696 v4 "
     "无 AVX-512）；产物 7754632 B 静态单文件，落 /data/vision/strata-vision（持久，非镜像层）；"
     "config 需同时有 vision 段，否则服务会广播图片却拒绝每一张（serve/server.py:2170 原话）",
     "W715 新启用"],
    ["V00", "CFG", "vision.exe", "/data/vision/strata-vision", "vision", "ADOPTED", "-", "-", "-",
     "编译产物路径（宿主 /home/albus/strata166/data/vision/strata-vision）", "W715 新启用"],
    ["V01", "CFG", "vision.mmproj",
     "/models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/mmproj-Qwen3.8-Flash-Next-BF16.gguf",
     "vision", "ADOPTED", "-", "-", "-",
     "sha256 b1a82259...（huihui 仓原文件）；与主模型同源配套（encoder 把图编码后喂给本模型）", "W715 新启用"],
    ["V02", "CFG", "vision.model", NEW_NATIVE, "vision", "ADOPTED", "-", "-", "-",
     "strata-vision 的 --model 参数 = 文本模型第一分片（tools/vision/strata_vision.cpp:7 用法行）", "W715 新启用"],
]
for r in new_rows:
    assert len(r) == ncol, "新增行列数不符: %r" % r
    assert not any(x[0] == r[0] for x in out), "id 冲突: %s" % r[0]
    out.append(r)

body = "\n".join([hdr] + ["\t".join(f) for f in out]) + "\n"

# 3) 五断言
assert body.count("\r") == 0, "CR 非 0"
BAN = [0x21D2, 0x2192, 0x2014, 0x2013, 0x2026, 0x2265, 0x2264, 0x2260, 0x2212, 0x00D7]
badc = [hex(ord(c)) for c in body if ord(c) in BAN]
assert not badc, "禁用码位: %r" % badc[:6]
assert len(out) == n0 - 1 + len(new_rows), "行数不符 %d" % len(out)
for k in ["huihui-ud-iq4_xs", "vision.mmproj", NEW_NATIVE]:
    assert k in body, "缺锚点 %s" % k

io.open(REG, "w", encoding="utf-8", newline="\n").write(body)

# 4) 读回自证
back = io.open(REG, encoding="utf-8").read()
assert back == body, "读回不相等"
print("行数 %d -> %d（新增 %d）" % (n0 - 1, len(out), len(new_rows)))
print("CR=%d  禁用码位=0" % back.count("\r"))
for c in changed:
    print("  改:", c)
st = {}
for f in out:
    st[f[5]] = st.get(f[5], 0) + 1
print("状态分布:", st)
