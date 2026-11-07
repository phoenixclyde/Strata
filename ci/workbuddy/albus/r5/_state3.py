import subprocess, base64
def sh(s, t=90):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
docker ps --format "{{.Names}}|{{.Image}}|{{.Status}}" | grep "strata166-407" | head -2
curl -s --max-time 5 http://127.0.0.1:8090/health | head -c 60; echo
curl -s --max-time 5 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;e=json.load(sys.stdin)['engine'];print('slots',e['expert_slots'],'vram',e['vram_free_mib'],'ver',e['version'])"
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
docker images | grep -E "0.2.4p4|0.2.4p5" | awk '{print $1, $2}'
'''))
