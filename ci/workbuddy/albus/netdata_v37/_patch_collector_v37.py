# -*- coding: utf-8 -*-
"""断言式补丁：rk-health-collect.sh v36 -> v37
新增：mem（/proc/meminfo 全量）、ssd（smartctl，60s 缓存）、prod_srv（生产服务进程数）、
      STRATA_SERVE 判据放宽（strata* --serve，含 strata-0.1.56-090 --serve）。
每条替换先断言 old 命中恰 1 次；写盘后读回断言新标记。
"""
import io, sys, hashlib, shutil, os

SRC = r"D:/workbuddy/netdata-dashboard/_166_ops_live/rk-health-collect.sh"
DST = r"D:/workbuddy_space/strata_ws/albus/netdata_v37/rk-health-collect.sh"

s = io.open(SRC, encoding="utf-8").read()
orig = s
shutil.copyfile(SRC, DST + ".v36.bak")

PAIRS = []

# ---- C1: 常驻 serve 判据放宽 + 生产服务进程数 ----
old1 = '''# [v36 2026-10-27] 常驻推理服务 strata --serve 的进程数（探针 BOX 三路判据**不认识它**，
#   2026-10-27 实测：serve 握 33.9GB / KFD 1 进程，探针判 IDLE + VRAM_LEAK rc=3）。
#   与探针的 RK_SERVE 同一手法（ps 现数、grep -v grep）；只报**原始计数**，页面只转述。
#   ps 走容器 --pid host，与宿主同视图；数不到（异常）由页面按 null 显示 --。
STRATA_SERVE=$(ps -eo args 2>/dev/null | grep -F "strata --serve" | grep -v grep | wc -l | tr -d " ")'''
new1 = '''# [v36 2026-10-27] 常驻推理服务 strata serve 的进程数（探针 BOX 三路判据**不认识它**，
#   2026-10-27 实测：serve 握 33.9GB / KFD 1 进程，探针判 IDLE + VRAM_LEAK rc=3）。
#   与探针的 RK_SERVE 同一手法（ps 现数、grep -v grep）；只报**原始计数**，页面只转述。
#   ps 走容器 --pid host，与宿主同视图；数不到（异常）由页面按 null 显示 --。
# [v37 2026-11-05] 判据放宽（实测漏检）：v36 用 `grep -F "strata --serve"` 只认**字面**那种
#   调用形态；生产容器里跑的是 `/data/bin/strata-0.1.56-090 --serve ...`（带版本号后缀）
#   => 命中 0 => 页面归因失效 => 顶栏在**生产服务常驻**时恒显「显存泄漏 3088x」红色假警。
#   现按「二进制名以 strata 开头 + 紧跟 --serve」匹配，两种形态都覆盖。
#   [!] 只数**持有显存的 --serve 本尊**，不数包装进程（server.py / strata-vision）。
STRATA_SERVE=$(ps -eo args 2>/dev/null | grep -E 'strata[A-Za-z0-9._-]* --serve' | grep -v grep | wc -l | tr -d " ")
# [v37] 生产推理服务的**包装进程**数（serve/server.py --engine strata，即 8090 那套）。
#   它本身不持 KFD，但它是「这台机在对外提供推理」的判据之一：容器名千变万化
#   （strata166-407 / arm-A / .pre-w920b），进程命令行更稳定。页面把两个计数**取或**。
PROD_SRV=$(ps -eo args 2>/dev/null | grep -F 'serve/server.py --engine strata' | grep -v grep | wc -l | tr -d " ")'''
PAIRS.append(("C1", "modify", old1, new1))

# ---- C2: mem + ssd 采集块 ----
old2 = '''SWAP_USED=$(free -b 2>/dev/null | awk '/^Swap:/{print $3}')
SWAP_TOTAL=$(free -b 2>/dev/null | awk '/^Swap:/{print $2}')'''
new2 = '''SWAP_USED=$(free -b 2>/dev/null | awk '/^Swap:/{print $3}')
SWAP_TOTAL=$(free -b 2>/dev/null | awk '/^Swap:/{print $2}')

# ---------- 3.5 内存全量 + SSD SMART（v37 2026-11-05） ----------
# 内存：直接读 /proc/meminfo（容器 --pid host、/proc 未隔离 => 与宿主同视图）。
#   为什么不沿用页面从 system.ram 四维反推：netdata 的 system.ram 只有 free/used/cached/buffers
#   四维，反推出的「总量」漏掉 SReclaimable/Slab；而它的 "used" 是 total-free-cached-buffers，
#   与 `free` 的 "used = total - available" 是两个口径（差在可回收缓存）。
#   页面原先用前者当「内存占用」，于是「缓存吃掉一半内存」时读数偏小、与实际观感不符。
#   这里给**原始量**，口径由页面显式声明（已用 = total - available，缓存单列）。
# SSD：镜像自带 smartctl（/usr/sbin/smartctl），但要 --device 才看得见块设备
#   （device cgroup；recreate_netdata.sh 已加 /dev/nvme0 /dev/nvme0n1 /dev/sda）。
#   60s 一刷：SMART 查询有成本，而温度/寿命/通电小时变化极慢；缓存落 /tmp。
SYS_JSON=$(RK_SSD_TTL="${RK_SSD_TTL:-60}" /usr/bin/python3 - <<'PY'
import json, os, subprocess, time

def mem():
    d = {}
    try:
        with open("/proc/meminfo") as fh:
            for ln in fh:
                k, v = ln.split(":", 1)
                p = v.strip().split()
                if p:
                    d[k] = int(p[0]) * 1024
    except Exception:
        return None
    def g(k):
        return d.get(k, 0)
    return {"total": g("MemTotal"), "free": g("MemFree"), "available": g("MemAvailable"),
            "buffers": g("Buffers"), "cached": g("Cached"), "sreclaim": g("SReclaimable"),
            "shmem": g("Shmem"), "slab": g("Slab"),
            "swap_total": g("SwapTotal"), "swap_free": g("SwapFree")}

CACHE = "/tmp/.rk_ssd_cache.json"

def one(dev):
    try:
        r = subprocess.run(["/usr/sbin/smartctl", "-j", "-a", "/dev/" + dev],
                           capture_output=True, timeout=10)
        d = json.loads((r.stdout or b"{}").decode("utf-8", "replace"))
    except Exception as e:
        return {"err": str(e)[:80]}
    dev_info = d.get("device") or {}
    out = {"model": d.get("model_name") or dev_info.get("model_name") or dev,
           "ok": 1 if (d.get("smart_status") or {}).get("passed") else 0}
    cap = d.get("user_capacity") or d.get("nvme_total_capacity")
    if isinstance(cap, dict):
        out["cap"] = cap.get("bytes")
    elif isinstance(cap, int):
        out["cap"] = cap
    out["temp"] = (d.get("temperature") or {}).get("current")
    proto = (dev_info.get("protocol") or "").lower()
    h = d.get("nvme_smart_health_information_log")
    if proto.startswith("nvme") or h:
        h = h or {}
        pu = h.get("percentage_used")
        out["kind"] = "nvme"
        out["life"] = None if pu is None else max(0, 100 - int(pu))
        out["spare"] = h.get("available_spare")
        duw = h.get("data_units_written")
        out["written"] = None if duw is None else int(duw) * 512000
        out["hours"] = h.get("power_on_hours")
        out["crit"] = h.get("critical_warning")
        out["media_err"] = h.get("media_errors")
    else:
        tab = (d.get("ata_smart_attributes") or {}).get("table") or []
        A = {}
        for x in tab:
            A[x.get("id")] = x
        def raw(i):
            x = A.get(i)
            return None if not x else (x.get("raw") or {}).get("value")
        out["kind"] = "sata"
        life = None
        for i in (231, 177):
            if i in A and A[i].get("value") is not None:
                life = int(A[i]["value"])
                break
        out["life"] = life
        out["hours"] = raw(9)
        out["written"] = None
        out["lba_w"] = raw(241)
        out["realloc"] = raw(5)
        out["spare"] = raw(180)
    return out

res = None
try:
    ttl = int(os.environ.get("RK_SSD_TTL") or 60)
    if time.time() - os.stat(CACHE).st_mtime < ttl:
        with open(CACHE) as fh:
            res = json.load(fh)
except Exception:
    res = None
if not res:
    res = {"ts": int(time.time()), "disks": {}}
    for dev in ("nvme0n1", "sda"):
        res["disks"][dev] = one(dev)
    try:
        with open(CACHE, "w") as fh:
            json.dump(res, fh)
    except Exception:
        pass
print(json.dumps({"mem": mem(), "ssd": res}, separators=(",", ":")))
PY
)'''
PAIRS.append(("C2", "insert", old2, new2))

# ---- C3: env 传递 ----
old3 = '''STRATA_SERVE="$STRATA_SERVE" \\'''
new3 = '''STRATA_SERVE="$STRATA_SERVE" PROD_SRV="$PROD_SRV" SYS_JSON="$SYS_JSON" \\'''
PAIRS.append(("C3", "modify", old3, new3))

# ---- C4: python 侧解析 SYS_JSON ----
old4 = '''tg = kv(os.environ.get("BLOB_TGT"))
d = {'''
new4 = '''tg = kv(os.environ.get("BLOB_TGT"))
# [v37] 内存全量 + SSD SMART（由 shell 段算好，紧凑 JSON 经 env 传入；解析失败按空处理，
#   页面据此显示 -- 且不置色 —— 与「取不到值不冒充 0」同规）。
try:
    SJ = json.loads(os.environ.get("SYS_JSON") or "{}")
except Exception:
    SJ = {}
d = {'''
PAIRS.append(("C4", "insert", old4, new4))

# ---- C5: JSON 新增 mem / ssd / prod_srv ----
old5 = '''        "strata_serve": i("STRATA_SERVE"),
    },'''
new5 = '''        "strata_serve": i("STRATA_SERVE"),
        # [v37] 生产推理服务包装进程数（serve/server.py --engine strata）。与 strata_serve
        #   取或构成「有服务在用卡」的判据；两者都是**原始计数**，判决仍归探针。
        "prod_srv": i("PROD_SRV"),
    },'''
PAIRS.append(("C5", "insert", old5, new5))

old6 = '''        "load1": f("LOAD1"), "uptime": i("UP"),
    },
}'''
new6 = '''        "load1": f("LOAD1"), "uptime": i("UP"),
    },
    # [v37] /proc/meminfo 全量（字节）。页面据此算「已用 = total - available」并把缓存单列，
    #   不再从 system.ram 四维反推（那条路漏 SReclaimable，且 used 口径与 free 不一致）。
    "mem": SJ.get("mem") or {},
    # [v37] 每块盘的 SMART 关键量（温度 / 寿命剩余 / 已写入 / 通电小时 / 备用块）。
    #   disks 下按设备名索引；取不到时该盘内是 {"err": "..."} => 页面 -- 且不置色。
    "ssd": SJ.get("ssd") or {},
}'''
PAIRS.append(("C6", "insert", old6, new6))

for tag, kind, old, new in PAIRS:
    n = s.count(old)
    assert n == 1, "%s OLD 命中 %d 次（应为 1）: %r" % (tag, n, old[:60])
    s = s.replace(old, new)
    if kind == "insert":
        for line in old.split("\n"):
            assert line.strip() in s, "%s 超集判据失败：丢了 %r" % (tag, line[:60])

io.open(DST, "w", encoding="utf-8", newline="\n").write(s)
back = io.open(DST, encoding="utf-8").read()
for tag, _, _, new in PAIRS:
    assert new.split("\n")[0] in back, "%s 写盘校验失败" % tag
print("OK  %s  %d -> %d bytes  md5=%s" % (DST, len(orig.encode()), len(back.encode()),
      hashlib.md5(back.encode()).hexdigest()))
