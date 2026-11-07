# -*- coding: utf-8 -*-
"""recreate_netdata.sh：补 CAP_SYS_RAWIO（SATA SMART 必需）+ 自证 5。
实测：容器内 `smartctl -d sat /dev/sda` 报 Read Device Identity failed: Operation not permitted
（内核 5.8+ 对块设备 SG_IO 要求 CAP_SYS_RAWIO）；NVMe 走 NVME_IOCTL_ADMIN_CMD 只需 SYS_ADMIN
（已有）。两者缺一都**不报错**，只是那几格静默 --。
注意顺序：$CA 在 SYSLOG 自证之前才赋值 => 本段必须插在**那条 esac 之后**，不能提前。"""
import io, hashlib, shutil, time

P = "/home/albus/netdata/ops/recreate_netdata.sh"
s = io.open(P, encoding="utf-8").read()
bak = P + ".bak_v37b_" + time.strftime("%Y%m%d_%H%M%S")
shutil.copyfile(P, bak)

pairs = []
old1 = "  --cap-add SYS_ADMIN --cap-add SYS_PTRACE --cap-add SYSLOG \\\n"
new1 = "  --cap-add SYS_ADMIN --cap-add SYS_PTRACE --cap-add SYSLOG --cap-add SYS_RAWIO \\\n"
pairs.append(("R1", old1, new1))

old2 = '''case "$CA" in
  *SYSLOG*) echo "SELFCHECK syslog_cap=OK" ;;
  *) echo "SELFCHECK syslog_cap=MISSING"; exit 9 ;;
esac'''
new2 = '''case "$CA" in
  *SYSLOG*) echo "SELFCHECK syslog_cap=OK" ;;
  *) echo "SELFCHECK syslog_cap=MISSING"; exit 9 ;;
esac
# 重建自证 5（v37 2026-11-05）：CAP_SYS_RAWIO 必须在。SATA 的 SMART 走 SG_IO，而内核 5.8+
#   对块设备的 SG_IO 要求 CAP_SYS_RAWIO（实测缺它：Read Device Identity failed:
#   Operation not permitted）。缺了不报错，只是 SATA 的温度/通电小时/备用块永远 --。
#   NVMe 走 NVME_IOCTL_ADMIN_CMD，只需 SYS_ADMIN（已在），故 NVMe 有没有这块 cap 都能读。
case "$CA" in
  *SYS_RAWIO*) echo "SELFCHECK sys_rawio=OK" ;;
  *) echo "SELFCHECK sys_rawio=MISSING"; exit 9 ;;
esac'''
pairs.append(("R2", old2, new2))

for tag, old, new in pairs:
    n = s.count(old)
    assert n == 1, "%s 命中 %d 次" % (tag, n)
    s = s.replace(old, new)

io.open(P, "w", encoding="utf-8").write(s)
back = io.open(P, encoding="utf-8").read()
assert "--cap-add SYS_RAWIO" in back and "SELFCHECK sys_rawio=OK" in back
i = back.find("CA=$(docker inspect")
j = back.find("SELFCHECK sys_rawio=OK")
assert i < j, "顺序错误：sys_rawio 自证在 CA 赋值之前"
print("BAK", bak)
print("OK", len(back), hashlib.md5(back.encode()).hexdigest())
