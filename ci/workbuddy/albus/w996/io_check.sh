#!/bin/bash
echo "===== diskstats 5 秒增量（扇区→MiB）====="
python3 - <<'PY'
import time
def rd():
    d = {}
    for l in open("/proc/diskstats"):
        p = l.split()
        if p[2] in ("nvme0n1p1", "sda3", "dm-0", "sda"):
            d[p[2]] = (int(p[5]), int(p[9]))  # sectors read, sectors written
    return d
a = rd(); time.sleep(5); b = rd()
for k in a:
    if k in b:
        r = (b[k][0] - a[k][0]) * 512 / 1048576.0
        w = (b[k][1] - a[k][1]) * 512 / 1048576.0
        print("%-12s read=%9.2f MiB/5s  write=%9.2f MiB/5s" % (k, r, w))
PY
echo
echo "===== Docker Root / 生产容器日志 ====="
docker info --format 'DockerRoot={{.DockerRootDir}} LogDriver={{.LoggingDriver}}'
docker inspect strata166-407 --format 'LogPath={{.LogPath}} Driver={{.HostConfig.LogConfig.Type}}'
echo
echo "===== 老盘(根卷)上正在被写的文件（近 10 分钟）====="
sudo find /var/lib/docker/containers /var/log -type f -mmin -10 2>/dev/null | head -12
echo
echo "===== 各容器日志大小 top ====="
sudo du -sh /var/lib/docker/containers/*/*-json.log 2>/dev/null | sort -rh | head -6
