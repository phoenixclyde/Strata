#!/bin/bash
P=/home/albus/routeK/run/_rk78_pollution.sh
echo "### PROBE_MD5"; md5sum $P; wc -c $P
echo "### PROBE_PATTERNS"; grep -nE 'CARS=|SERVES=|RKN=|RK_CAR_CONTAINER_N|BOX_STATE=|WHO_DESC|VRAM_LEAK|VRAM_WARN' $P | head -40
echo "### IMG"; docker inspect -f '{{.Image}}' netdata
echo "### TEST_NVME"; docker run --rm --device /dev/nvme0 --device /dev/nvme0n1 --cap-add SYS_RAWIO --entrypoint sh $(docker inspect -f '{{.Image}}' netdata) -c 'smartctl -j -a /dev/nvme0n1 2>&1 | grep -E "\"(percentage_used|available_spare|temperature|data_units_written|power_on_time|critical_warning)" -A2 | head -40' 2>&1 | tail -20
echo "### TEST_SDA"; docker run --rm --device /dev/sda --cap-add SYS_RAWIO --entrypoint sh $(docker inspect -f '{{.Image}}' netdata) -c 'smartctl -j -A /dev/sda 2>&1 | head -20' 2>&1 | tail -22
echo "### DISKIO"; curl -s 'http://127.0.0.1:19999/api/v1/data?chart=disk.sda&after=-1&points=1&format=json' | head -c 600; echo
echo "### SYSIO"; curl -s 'http://127.0.0.1:19999/api/v1/data?chart=system.io&after=-1&points=1&format=json' | head -c 600; echo
echo "### RAM"; curl -s 'http://127.0.0.1:19999/api/v1/data?chart=system.ram&after=-1&points=1&format=json' | head -c 800; echo
echo "### RAPL"; curl -s 'http://127.0.0.1:19999/api/v1/data?chart=cpu.powercap_intel_rapl_zone_package-0&after=-1&points=1&format=json' | head -c 500; echo
echo "### DRAM"; curl -s 'http://127.0.0.1:19999/api/v1/data?chart=cpu.powercap_intel_rapl_subzones_package-0&after=-1&points=1&format=json' | head -c 500; echo
