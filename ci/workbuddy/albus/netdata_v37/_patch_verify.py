# -*- coding: utf-8 -*-
"""verify_netdata.sh：补 v37 的四条语义判据（只加检查，不改既有项）。
纪律（README §9.10 B）：自测器必须断言**被测对象的语义**，不能只断言「文件存在且新鲜」——
否则 health.json 里 mem/ssd 全是 null 也照样全绿。"""
import io, hashlib, shutil, time

P = "/home/albus/netdata/ops/verify_netdata.sh"
s = io.open(P, encoding="utf-8").read()
bak = P + ".bak_v37_" + time.strftime("%Y%m%d_%H%M%S")
shutil.copyfile(P, bak)

old = '''# ---------------------------------------------------------------- 汇总'''
new = '''# ---------------------------------------------------------------- 10.9 v37 新增面（2026-11-05）
# 四块新增数据的**语义**判据。写在这里的理由与 README §9.10 B 同：只检查「文件在、ts 新」
# 对「mem/ssd 全是 null」是盲的 —— 那正是上一轮探针失效时不报红的同型缺陷。
MTO=$(printf '%s' "$HJ" | sed -n 's/.*"mem":{"total":\\([0-9]*\\).*/\\1/p' | head -n 1)
MAV=$(printf '%s' "$HJ" | sed -n 's/.*"available":\\([0-9]*\\).*/\\1/p' | head -n 1)
chk health_mem "$([ -n "$MTO" ] && [ "${MTO:-0}" -gt 0 ] && [ -n "$MAV" ] && [ "${MAV:-0}" -gt 0 ] && echo 0 || echo 1)" \\
    "mem.total=${MTO:-<空>} available=${MAV:-<空>}（都要 >0；空=采集器 mem 段没产出）"
# SSD：要求两块盘都出现，且温度/寿命是数字（不是 null）。取不到时 ssd.disks 里是 {"err":...}。
SNV=$(printf '%s' "$HJ" | sed -n 's/.*"nvme0n1":{"model":"[^"]*","ok":[0-9]*,"cap":[0-9]*,"temp":\\([0-9]*\\).*/\\1/p' | head -n 1)
SSD=$(printf '%s' "$HJ" | sed -n 's/.*"sda":{"model":"[^"]*","ok":[0-9]*,"cap":[0-9]*,"temp":\\([0-9]*\\).*/\\1/p' | head -n 1)
chk health_ssd_temp "$([ -n "$SNV" ] && [ -n "$SSD" ] && echo 0 || echo 1)" \\
    "nvme0n1=${SNV:-<无>}°C sda=${SSD:-<无>}°C（空=对应盘的 smartctl 取不到）"
SLF=$(printf '%s' "$HJ" | sed -n 's/.*"sda":{[^}]*"life":\\([0-9]*\\).*/\\1/p' | head -n 1)
NLF=$(printf '%s' "$HJ" | sed -n 's/.*"nvme0n1":{[^}]*"life":\\([0-9]*\\).*/\\1/p' | head -n 1)
chk health_ssd_life "$([ -n "$SLF" ] && [ -n "$NLF" ] && echo 0 || echo 1)" \\
    "nvme0n1 寿命剩余=${NLF:-<无>}% sda=${SLF:-<无>}%（空=寿命维读不到，多半是缺 CAP_SYS_RAWIO）"
PRD=$(printf '%s' "$HJ" | sed -n 's/.*"prod_srv":\\([0-9]*\\).*/\\1/p' | head -n 1)
chk health_prod_srv "$([ -n "$PRD" ] && echo 0 || echo 1)" \\
    "poll.prod_srv=${PRD:-<空>}（生产推理包装进程数；空=采集器没产出，顶栏无法归因）"
BDEV=$(printf '%s' "$DEV" | grep -o '"PathOnHost":"/dev/\\(nvme0\\|nvme0n1\\|sda\\)"' | wc -l | tr -d ' ')
chk dev_block "$([ "$BDEV" = "3" ] && echo 0 || echo 1)" "块设备映射=$BDEV/3（缺则 SMART 静默 --）"

# ---------------------------------------------------------------- 汇总'''
assert s.count(old) == 1, s.count(old)
s = s.replace(old, new)
io.open(P, "w", encoding="utf-8").write(s)
back = io.open(P, encoding="utf-8").read()
assert "chk health_ssd_life" in back and "chk dev_block" in back
print("BAK", bak)
print("OK", len(back), hashlib.md5(back.encode()).hexdigest())
