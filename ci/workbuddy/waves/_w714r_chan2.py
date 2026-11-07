# 通道选优：scp / ssh 原始字节单流 / ssh 原始字节 8 进程并行，各传 128MB
import concurrent.futures as cf, hashlib, os, subprocess, time

BASE = ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
        "-o", "ServerAliveInterval=15"]
HOST = "albus@192.168.50.166"
SSH = BASE + [HOST]
TMP = "/home/albus/strata166/tmp_sp_%d.bin"
blob = os.urandom(8 << 20) * 16   # 128 MB
md5 = hashlib.md5(blob).hexdigest()
print("样本 128 MB, md5=%s" % md5)


def codec(args, data, t=900):
    t0 = time.time()
    p = subprocess.run(args, input=data, capture_output=True, timeout=t)
    return p.returncode, time.time() - t0


def rep(lab, rc, dt, nbytes):
    print("  %-28s rc=%d  %5.2fs  => %6.1f MB/s" % (lab, rc, dt, nbytes / dt / 1e6))


# 1) ssh 原始字节，单流
rep("ssh raw x1", *codec(SSH + ["cat > " + (TMP % 90)], blob), len(blob))

# 2) ssh 原始字节，8 流并行（进程池）
def one(i):
    return codec(SSH + ["cat > " + (TMP % i)], blob)
t0 = time.time()
with cf.ThreadPoolExecutor(max_workers=8) as ex:
    rs = list(ex.map(one, range(8)))
dt = time.time() - t0
print("  %-28s wall %5.2fs  => %6.1f MB/s  各路 %s"
      % ("ssh raw x8", dt, len(blob) * 8 / dt / 1e6, " ".join("%.2f" % r[1] for r in rs)))

# 3) scp
open(r"D:/workbuddy_space/strata_ws/deploy/tmp/_sp.bin", "wb").write(blob)
t0 = time.time()
p = subprocess.run(["C:/Program Files/Git/usr/bin/scp.exe", "-o", "BatchMode=yes",
                    "-o", "ConnectTimeout=15", r"D:/workbuddy_space/strata_ws/deploy/tmp/_sp.bin",
                    HOST + ":" + (TMP % 99)], capture_output=True, timeout=900)
rep("scp x1", p.returncode, time.time() - t0, len(blob))
if p.stderr.strip():
    print("     scp stderr:", p.stderr.decode("utf-8", "replace")[-200:])

# 校验 + 清理
sc = "set -u\nfor f in " + " ".join(TMP % i for i in list(range(8)) + [90, 99]) + "; do [ -f $f ] && echo \"$(basename $f) $(stat -c %s $f) $(md5sum $f|cut -d' ' -f1)\"; done\nrm -f " + " ".join(TMP % i for i in list(range(8)) + [90, 99]) + "\n"
p = subprocess.run(SSH + ["bash -s"], input=sc.encode(), capture_output=True, timeout=120)
print(p.stdout.decode())
print("(期望 md5 均为 %s；临时文件已清理)" % md5)
