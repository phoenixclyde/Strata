# W716：B6 结论落 register（P30 CANDIDATE -> REJECTED 不适用）。归档 + 五断言
import io, os, shutil, time

REG = r"D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv"
BAK = REG + ".bak_w716_" + time.strftime("%Y%m%d_%H%M%S")

EV = ("W716 源码级判定（读源码即判，无需发车）：native_mmvq.cu 的编译边界 "
      "#if !defined(__HIPCC__) ... #else // HIP: no interleaved path => 该分支下 "
      "native_mmvq_il_supported() 直接 return false（2644 行），且 native_q8_1_interleave() 会抛 "
      "\"native_q8_1_interleave is CUDA only\"（2643 行）。我们 166 的构建是 HIP => 条件 "
      "`g_mmvq_il() && native_mmvq_il_supported(...)`（verify.cpp:952 / 1604）恒为假，永远走 native_mmvq() "
      "普通路径。旁证：g_mmvq_il() 自身默认 on（verify.cpp:107，未设或非 '0' 即 true），所以\"默认值\"这件事对本机无意义；"
      "运行期也从未出现该异常。")
VD = "本机结构上不可能命中（编译期即定，非\"未验\"）=> 不适用"

raw0 = io.open(REG, encoding="utf-8").read()
n0 = len(raw0.splitlines())
shutil.copy2(REG, BAK)
assert io.open(BAK, encoding="utf-8").read() == raw0, "归档不一致"
print("归档 -> %s" % os.path.basename(BAK))

lines = raw0.splitlines()
hdr = lines[0]
ncol = len(hdr.split("\t"))
out, hit = [], 0
for ln in lines[1:]:
    if not ln.strip():
        continue
    f = ln.split("\t")
    assert len(f) == ncol, "列数不符: %r" % ln[:60]
    if f[0] == "P30":
        assert f[5] == "CANDIDATE", "P30 状态不是 CANDIDATE: %r" % f[5]
        f[3] = "(不适用)"
        f[5] = "REJECTED"
        f[9] = EV
        f[10] = VD
        hit += 1
    out.append(f)
assert hit == 1, "P30 命中 %d 次" % hit

body = "\n".join([hdr] + ["\t".join(f) for f in out]) + "\n"
assert body.count("\r") == 0
BAN = [0x21D2, 0x2192, 0x2014, 0x2013, 0x2026, 0x2265, 0x2264, 0x2260, 0x2212, 0x00D7]
bad = [hex(ord(c)) for c in body if ord(c) in BAN]
assert not bad, "禁用码位 %r" % bad[:6]
assert len(out) == n0 - 1, "行数变了"
io.open(REG, "w", encoding="utf-8", newline="\n").write(body)
back = io.open(REG, encoding="utf-8").read()
assert back == body, "读回不一致"

st = {}
for f in out:
    st[f[5]] = st.get(f[5], 0) + 1
print("行数 %d（不变）；状态分布 %s" % (len(out), st))
print("P30 新行:")
for f in out:
    if f[0] == "P30":
        print("   ", "\t".join(f)[:150], "...")
import hashlib
print("register md5 =", hashlib.md5(back.encode("utf-8")).hexdigest())
