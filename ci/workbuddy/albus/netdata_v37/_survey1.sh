#!/bin/bash
echo "### DATE"; date; uptime
echo "### FREE_M"; free -m
echo "### MEMINFO"; grep -E '^(MemTotal|MemFree|MemAvailable|Buffers|Cached|SReclaimable|Shmem|SwapTotal|SwapFree|Committed_AS|CommitLimit)' /proc/meminfo
echo "### LSBLK"; lsblk -d -o NAME,MODEL,SIZE,ROTA,TRAN
echo "### LSBLK_ALL"; lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS
echo "### DF"; df -h / /home 2>/dev/null
echo "### SMARTCTL"; command -v smartctl || echo NO_SMARTCTL
echo "### NVME_INFO"; sudo -n smartctl -i /dev/nvme0n1 2>&1 | head -30
echo "### NVME_HEALTH"; sudo -n smartctl -A /dev/nvme0n1 2>&1 | head -40
echo "### SDA_INFO"; sudo -n smartctl -i /dev/sda 2>&1 | head -30
echo "### SDA_HEALTH"; sudo -n smartctl -A /dev/sda 2>&1 | head -45
echo "### HWMON"; for d in /sys/class/hwmon/hwmon*; do printf "%s name=%s\n" "$d" "$(cat $d/name 2>/dev/null)"; done
echo "### POWERCAP"; for d in /sys/class/powercap/*/; do [ -f "$d/name" ] && printf "%s %s %s\n" "$d" "$(cat $d/name)" "$(cat $d/energy_uj 2>/dev/null)"; done
echo "### DRM"; ls /sys/class/drm
echo "### ROCM_PIDS"; sudo -n rocm-smi --showpids 2>&1 | tail -25
echo "### VRAM"; for d in /sys/class/drm/card*/device; do [ -f "$d/vendor" ] && printf "%s vendor=%s vram_used=%s\n" "$d" "$(cat $d/vendor)" "$(cat $d/mem_info_vram_used 2>/dev/null)"; done
echo "### STRATA_PS"; ps -eo pid,rss,etime,args | grep -E 'strata|serve' | grep -v grep
echo "### DOCKER"; sudo -n docker ps --format '{{.Names}} {{.Image}} {{.Status}}'
echo "### NVIDIA"; nvidia-smi --query-gpu=name,power.draw,temperature.gpu,utilization.gpu --format=csv,noheader
echo "### SENSORS"; command -v sensors >/dev/null && sensors 2>/dev/null | head -60 || echo NO_SENSORS
