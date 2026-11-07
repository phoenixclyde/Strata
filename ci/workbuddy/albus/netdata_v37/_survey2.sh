#!/bin/bash
echo "### NPROC"; nproc; lscpu | grep -E 'Model name|^CPU\(s\)|Thread|Core'
echo "### IPMI_BIN"; command -v ipmitool || echo NO_IPMITOOL
echo "### IPMI_DEV"; ls -l /dev/ipmi* 2>/dev/null || echo NO_IPMI_DEV
echo "### MODULES"; lsmod | grep -E 'ipmi|coretemp|nvme|drivetemp' 
echo "### DMI"; sudo -n dmidecode -t baseboard 2>/dev/null | grep -E 'Manufacturer|Product Name|Version' | head -6
echo "### IPMI_SENSOR"; sudo -n ipmitool sensor 2>&1 | grep -iE 'power|watt|curr' | head -20
echo "### IPMI_DCMI"; sudo -n ipmitool dcmi power reading 2>&1 | head -12
echo "### SDA_HEALTH_TAIL"; sudo -n smartctl -A /dev/sda 2>&1 | tail -18
echo "### SDA_ATTR_241"; sudo -n smartctl -A /dev/sda 2>&1 | grep -E '241|242|243|9 '
echo "### NVME_JSON"; sudo -n smartctl -j -a /dev/nvme0n1 2>&1 | head -40
echo "### CT_SMARTCTL"; docker exec netdata sh -c 'command -v smartctl || echo NONE' 2>&1
echo "### CT_DEV"; docker exec netdata sh -c 'ls -l /dev/nvme* /dev/sda 2>&1' 2>&1
echo "### CT_CAPS"; docker inspect -f '{{json .HostConfig.CapAdd}} {{json .HostConfig.Devices}}' netdata
echo "### CT_HOSTNAME_PS"; ps -eo pid,args | grep -E 'strata|vllm|serve_27b' | grep -v grep
echo "### DOCKER_ALL"; sudo -n docker ps -a --format '{{.Names}} | {{.Status}}'
