#!/bin/bash
IMG=$(docker inspect -f '{{.Image}}' netdata)
echo "### SOCKETS"; lscpu | grep -E 'Socket|NUMA|Core|Thread'
echo "### RAPL_ZONES"; ls /sys/class/powercap/
echo "### NVME_SYSADMIN"; docker run --rm --device /dev/nvme0 --device /dev/nvme0n1 --cap-add SYS_ADMIN --entrypoint sh "$IMG" -c 'smartctl -j -a /dev/nvme0n1 2>&1 | tail -40' 2>&1 | tail -45
echo "### SDA_NORAWIO"; docker run --rm --device /dev/sda --entrypoint sh "$IMG" -c 'smartctl -j -A /dev/sda >/tmp/o 2>/tmp/e; echo rc=$?; tail -5 /tmp/e; grep -c . /tmp/o' 2>&1 | tail -8
echo "### SDA_JSON_KEYS"; sudo -n smartctl -j -A /dev/sda 2>/dev/null | python3 -c "
import json,sys
d=json.load(sys.stdin)
a=d.get('ata_smart_attributes',{}).get('table',[])
for x in a:
    if x['id'] in (5,9,177,180,194,231,241,242):
        print(x['id'], x['name'], 'value=',x['value'],'worst=',x['worst'],'raw=',x['raw'])
print('temp',d.get('temperature'))
"
echo "### NVME_JSON_KEYS"; sudo -n smartctl -j -a /dev/nvme0n1 2>/dev/null | python3 -c "
import json,sys
d=json.load(sys.stdin)
for k in ('critical_warning','temperature','available_spare','available_spare_threshold','percentage_used','data_units_read','data_units_written','power_on_time','power_cycles','media_errors'):
    print(k,'=',d.get(k))
print('nvme_smart', json.dumps(d.get('nvme_smart_health_information_log'),ensure_ascii=False)[:400])
"
