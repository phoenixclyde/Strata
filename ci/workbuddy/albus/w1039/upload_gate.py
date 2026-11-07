import subprocess

r = subprocess.run(["scp", "-q", "albus/w1039/window_kvg.sh",
                    "albus@192.168.50.166:/home/albus/strata166/tmp/w1039/"],
                   capture_output=True, text=True, timeout=60)
print("scp rc", r.returncode, r.stderr[:200])

r = subprocess.run(["ssh", "-n", "-o", "ConnectTimeout=8", "albus@192.168.50.166",
                    "bash -n /home/albus/strata166/tmp/w1039/window_kvg.sh; echo SYN=$?"],
                   capture_output=True, text=True, timeout=60)
print(r.stdout.strip()[:300])

r = subprocess.run(["ssh", "-n", "-o", "ConnectTimeout=8", "albus@192.168.50.166",
                    "grep -c 'elastic K/V' /home/albus/strata166/tmp/w1039/window_kvg.sh"],
                   capture_output=True, text=True, timeout=60)
print("gate occurrences:", r.stdout.strip()[:40])
