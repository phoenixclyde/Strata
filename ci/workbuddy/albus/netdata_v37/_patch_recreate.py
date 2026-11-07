# -*- coding: utf-8 -*-
"""在 166 上就地给 recreate_netdata.sh 加三块块设备 + 重建自证 4。
只改 run 命令行与自证段，**不动 IMG=**（陷阱 B：远端 IMG 由 build_image.sh 就地改写，
本机副本恒滞后，整文件覆盖会把容器钉回旧镜像）。"""
import io, hashlib, shutil, time

P = "/home/albus/netdata/ops/recreate_netdata.sh"
s = io.open(P, encoding="utf-8").read()
bak = P + ".bak_v37_" + time.strftime("%Y%m%d_%H%M%S")
shutil.copyfile(P, bak)

pairs = []

old1 = "  --device /dev/kfd --device /dev/dri \\\n"
new1 = ("  --device /dev/kfd --device /dev/dri \\\n"
        "  --device /dev/nvme0 --device /dev/nvme0n1 --device /dev/sda \\\n")
pairs.append(("D1", old1, new1))

old2 = '''case "$DV" in
  *'"PathOnHost":"/dev/kfd"'*) echo "SELFCHECK kfd=OK" ;;'''
new2 = '''# 重建自证 4（v37 2026-11-05）：块设备必须在。
#   存储卡的温度/寿命/通电小时靠容器内 smartctl，而 smartctl 打开设备需要 device cgroup
#   放行（**nsenter 不切 cgroup**，宿主机 /host/root/dev 里看得见节点也没用）。
#     /dev/nvme0    -> NVMe admin passthrough（百分比磨损 / 累计写入）；缺了只能读到温度
#     /dev/nvme0n1  -> NVMe 命名空间（smartctl -a 的入口）
#     /dev/sda      -> SATA 的 SMART 属性（温度 / 通电小时 / 备用块）
#   三者缺任一个都**不会报错**，只在页面上静默显示 --（与 kfd 那条同族）。
NDEV=$(printf '%s' "$DV" | grep -o '"PathOnHost":"/dev/\\(nvme0\\|nvme0n1\\|sda\\)"' | wc -l | tr -d ' ')
if [ "$NDEV" -ge 3 ]; then echo "SELFCHECK block_devs=OK ($NDEV)"; else echo "SELFCHECK block_devs=MISSING ($NDEV)"; exit 9; fi
case "$DV" in
  *'"PathOnHost":"/dev/kfd"'*) echo "SELFCHECK kfd=OK" ;;'''
pairs.append(("D2", old2, new2))

for tag, old, new in pairs:
    n = s.count(old)
    assert n == 1, "%s 命中 %d 次" % (tag, n)
    s = s.replace(old, new)

io.open(P, "w", encoding="utf-8").write(s)
back = io.open(P, encoding="utf-8").read()
for tag, _, new in pairs:
    assert new.split("\n")[0] in back, tag
assert "--device /dev/nvme0n1" in back
print("BAK", bak)
print("OK", P, len(back), hashlib.md5(back.encode()).hexdigest())
print("IMG_LINE:", [l for l in back.split("\n") if l.startswith("IMG=")])
