# 并行多流 ssh 上传聚合带宽测试：N 路各传 128MB，比较 N=1/4/8
import base64, concurrent.futures as cf, hashlib, os, subprocess, time

SSH = ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
       "-o", "ServerAliveInterval=15", "albus@192.168.50.166"]
TMP = "/home/albus/strata166/tmp_speedtest_%d.bin"

blob = os.urandom(8 << 20) * 16   # 128 MB


def one(i, n=1):
    payload = base64.b64encode(blob) if n == 1 else base64.b64encode(blob)
    t0 = time.time()
    p = subprocess.run(SSH + ["base64 -d > " + (TMP % i)], input=payload, capture_output=True, timeout=900)
    return p.returncode, time.time() - t0, len(blob)


for N in (1, 4, 8):
    n_each = 1 if N == 1 else (1 if N == 4 else 1)
    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=N) as ex:
        res = list(ex.map(lambda i: one(i), range(N)))
    dt = time.time() - t0
    tot = sum(r[2] for r in res)
    print("N=%-2d  总实质 %6.1f MB  wall %5.2fs  聚合 %6.1f MB/s   各路(%s)"
          % (N, tot / 1e6, dt, tot / dt / 1e6, " ".join("%.2f" % r[1] for r in res)))

# 清理
subprocess.run(SSH + ["base64 -d | bash"],
               input=base64.b64encode(("rm -f " + " ".join(TMP % i for i in range(8)) + "\n").encode()) + b"\n",
               capture_output=True, timeout=60)
print("(临时文件已清理)")
