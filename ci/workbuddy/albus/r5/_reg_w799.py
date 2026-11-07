import io, shutil, time, subprocess, sys, json
REG = "deploy/params/PARAM_REGISTER.tsv"
rows = [dict(
 id="P126", scope="ARG", name="--conversation-cache-park-gain", value="256", family="serve/multiturn", status="PENDING",
 requires="--conversation-cache-mib 4096 / slots 4", conflicts="-", synergizes="-",
 evidence=("【W799 实测 2026-10-25 21:2x-21:4x，p4 镜像，8K 建会话 + 只变 read 长度 46/108/237/529/1008/1954，reused 固定 7577】"
           " 先量到地板：read=46 时 prompt_ms **917.8**（19.95 ms/token，是冷读 1.52 的 13.8 倍），单价随 read 单调降 19.95->2.22 => 截距约 **900 ms**。"
           " 地板的一半是 KV snapshot：引擎逐字 `parked 7589 tokens in 222.9 ms; snapshot_bytes=330210608 reused_kv_bytes=0`，每轮 park 一次、下一轮读回 => 约 450 ms。"
           " park-gain=256：park 行数 **8->5**，read=108/237/529 **-13.6% / -10.8% / -10.3%**，"
           "但**地板未动**（934 vs 918）、read=1954 **+3.3%**。"),
 verdict=("**PENDING，不采纳**。理由：①单样本（每档 1 次）；②地板未动说明 park 不是主因；③大 read 反向；"
          "④我的 set_gain 有 bug（只删参数名未删旧值），gain=1024 那臂的 args 残留 `'256'`，只有 256 臂数据干净。"
          "参数只改「何时 park」、不改任何计算 => 位一致、无质量风险，复测只需时间判据。"
          "另记两条挂账：`reused_kv_bytes=0`（增量快照的保留未改动页从未生效，每轮全量 330MB）；"
          "`pin=` 机制（generate.cpp:12735）专为同前缀兄弟查询设计、**完全不 park**，但需要客户端在请求里带 `pin=N`，当前前端不配合。")),
]
bak = REG + ".bak_w799_" + time.strftime("%Y%m%d_%H%M%S")
shutil.copy2(REG, bak)
lines = io.open(REG, encoding="utf-8-sig").read().splitlines()
hdr, old = lines[0], [l for l in lines[1:] if l.strip()]
ids = {l.split("\t")[0] for l in old}
out = []
for r in rows:
    assert r["id"] not in ids
    f = [r[k] for k in ("id","scope","name","value","family","status","requires","conflicts","synergizes","evidence","verdict")]
    assert len(f) == 11
    for x in f: assert "\t" not in x and "\n" not in x
    out.append("\t".join(f)); ids.add(r["id"])
io.open(REG, "w", encoding="utf-8", newline="\n").write("\n".join([hdr] + old + out) + "\n")
chk = io.open(REG, encoding="utf-8-sig").read().splitlines()
bad = [i+1 for i, l in enumerate(chk) if len(l.split("\t")) != 11]
allids = [l.split("\t")[0] for l in chk[1:] if l.strip()]
assert not bad and len(allids) == len(set(allids))
print("REGISTER OK rows=%d bak=%s" % (len(allids), bak.split("/")[-1]))
q = subprocess.run([sys.executable, "deploy/params/gen_config.py", "--write"], capture_output=True, text=True)
print("gen rc", q.returncode)
d = json.load(open("deploy/params/generated/strata-huihui-ud-iq4_xs.json"))
print("env n=%d args_tail=%s" % (len(d["env"]), d["args"][-3:]))
