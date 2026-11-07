# -*- coding: utf-8 -*-
"""W794：register 增 P110（注意力布局置换采纳）/ P111（reduce12 否决），然后 gen_config --write。"""
import io, shutil, time, subprocess, sys

REG = r"D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv"
ARMED = ("【W794 实测 2026-10-25 16:54-17:04，p4 镜像内三臂交错 A B C（各臂独立 restart，M 档 21,822 tokens，"
         "唯一 nonce reused=0，governor=schedutil）】")

E110 = (ARMED + " A（关）qsa attn **6742 / 6743 ms**（两次几乎逐毫秒相同）、prompt_ms 34910/34459；"
        "B（开）qsa attn **6202（-8.0%）**、prompt_ms 33954（-2.7%）。**其余相位一个没动**"
        "（hc read 2624/2624、qsa select 702/702、gdn 3722/3758）=> 只命中注意力。needle 32k@50% FOUND（53 s）。"
        "上游 #1661 逐字：同一开关在 int8 池上「内核组件 +14.65%，全模型提示 +1.19%，输出逐位一致」。"
        "我们原来用不了：`qsa_decode_attn.cu:969` 的判定逐字要求 `kv_mode == 1`，而 `--kv k8v4` 是 KV_MODE 3；"
        "置换本身是 q 在 LDS 里的双射 XOR（`sd = d ^ ((d >> 3) & 4)`）加读侧 `qflip = lane & 4` 还原，与 KV 格式无关，"
        "故 p4 补丁把它放开到 mode 3。")

V110 = ("采纳。**注意：本地无法验证「逐位一致」** —— 实测同一容器同一 env 连发三次同一条贪婪请求，输出 sha16 出现 "
        "2 次 a108be5b / 1 次 9f1f1d0c（长度 15/17），即引擎本身跨请求不确定（专家驻留路径差异，见 W767 §4.1 同类观察）"
        "=> 哈希对比不是有效的位等价判据。本次门槛改用 needle（32k，FOUND）+「只动 qsa attn」的相位证据 + 上游的位一致声明。")

E111 = (ARMED + " C（swizzle+reduce12）qsa attn **11764 ms（+74%）**、prompt_ms 39121（+12%）。"
        "reduce12 是把 12 个 head 的 lane 和用 16 次 shuffle 归约的换法，在 mode 1 上有效；"
        "放到 mode 3（q4_0 的 V 在 gather 时反量化成 fp16）明显更差 —— 很可能它假定了 int8 V 的 lane 到 head 的映射。")

rows = [
    dict(id="P110", scope="ENV", name="STRATA_GFX906_ATTN_QUERY_SWIZZLE", value="1", family="prefill",
         status="ADOPTED", requires="p4 镜像(patch_gfx906_attn_swizzle.py)", conflicts="-",
         synergizes="P103/P107", evidence=E110, verdict=V110),
    dict(id="P111", scope="ENV", name="STRATA_GFX906_ATTN_REDUCE12", value="1", family="prefill",
         status="REJECTED", requires="P110", conflicts="-", synergizes="-", evidence=E111,
         verdict="否决（+74%）。与 `P109`（SIMT）同理：gfx906 专用优化都围绕 int8 池设计，k8v4 上不能照搬。"),
]


def main():
    bak = REG + ".bak_w794_" + time.strftime("%Y%m%d_%H%M%S")
    shutil.copy2(REG, bak)
    lines = io.open(REG, encoding="utf-8-sig").read().splitlines()
    ids = {ln.split("\t")[0] for ln in lines[1:] if ln.strip()}
    out = []
    for r in rows:
        assert r["id"] not in ids, r["id"]
        f = [r[k] for k in ("id", "scope", "name", "value", "family", "status", "requires", "conflicts",
                            "synergizes", "evidence", "verdict")]
        assert len(f) == 11
        for x in f:
            assert "\t" not in x and "\n" not in x
        out.append("\t".join(f))
        ids.add(r["id"])
    lines.extend(out)
    io.open(REG, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    chk = io.open(REG, encoding="utf-8-sig").read().splitlines()
    bad = [i + 1 for i, ln in enumerate(chk) if len(ln.split("\t")) != 11]
    allids = [ln.split("\t")[0] for ln in chk[1:] if ln.strip()]
    assert not bad, bad[:5]
    assert len(allids) == len(set(allids))
    for p in ("P110", "P111"):
        assert p in allids, p
    print("REGISTER OK rows=%d bak=%s" % (len(allids), bak))
    q = subprocess.run([sys.executable, r"D:/workbuddy_space/strata_ws/deploy/params/gen_config.py", "--write"],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(q.stdout.decode("utf-8", "replace")[-420:])
    assert q.returncode == 0


main()
