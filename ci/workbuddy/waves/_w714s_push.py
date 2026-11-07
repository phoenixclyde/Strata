# 真传：D 盘 huihui 那份的 00002/00003 -> 166 的 huihui 目录
# 通道 = ssh 原始字节，8 进程并行；块 2GiB，dd 按偏移直写（无 part 中转，峰值只占目标文件本身）
import concurrent.futures as cf, os, subprocess, time

SSH = ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
       "-o", "ServerAliveInterval=15", "albus@192.168.50.166"]
LOCAL = r"D:/Qwen3.8-Flash-Next-UD-IQ4_XS"
RDIR = "/models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/unsloth-UD-IQ4_XS"
LOG = r"D:/workbuddy_space/strata_ws/deploy/tmp/_w714_push_huihui.log"

MIB = 1 << 20
CHUNK = 2048 * MIB
JOBS = 8
FILES = [
    ("Qwen3.8-Flash-Next-UD-IQ4_XS-00002-of-00003.gguf",
     "c67b468b3b83bc12a987e455ec4a0c2c3937250da1c234ae1638d9505180c161"),
    ("Qwen3.8-Flash-Next-UD-IQ4_XS-00003-of-00003.gguf",
     "130560b6a447e0febf61de9b03476f52143160bc4bcbacc9bfa07d9538718e2c"),
]

log = open(LOG, "w", encoding="utf-8", newline="\n")


def say(s):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), s)
    print(line, flush=True)
    log.write(line + "\n"); log.flush()


def push_chunk(local, start, length, off_mib, remote):
    cmd = "dd of='%s' bs=1M seek=%d conv=notrunc status=none" % (remote, off_mib)
    last = None
    for attempt in (1, 2):
        try:
            p = subprocess.Popen(SSH + [cmd], stdin=subprocess.PIPE,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            with open(local, "rb") as f:
                f.seek(start)
                left = length
                while left > 0:
                    b = f.read(min(64 << 20, left))
                    if not b:
                        break
                    p.stdin.write(b)
                    left -= len(b)
            p.stdin.close()
            rc = p.wait()
            if rc == 0:
                return True, length
            last = "rc=%d" % rc
        except Exception as e:
            last = repr(e)
        say("   重试 %s off=%dMiB (%s)" % (os.path.basename(local), off_mib, last))
    return False, last


say("START 目标=%s 文件=%d 块=%.0fMiB 并发=%d" % (RDIR, len(FILES), CHUNK / MIB, JOBS))
t_all = time.time()
for name, want_sha in FILES:
    lp = os.path.join(LOCAL, name)
    rp = RDIR + "/" + name
    sz = os.path.getsize(lp)
    tasks = []
    off = 0
    while off < sz:
        ln = min(CHUNK, sz - off)
        tasks.append((off, ln, off // MIB))
        off += ln
    say("-- %s  size=%d  块数=%d" % (name, sz, len(tasks)))
    t0 = time.time()
    done = 0
    ok_all = True
    with cf.ThreadPoolExecutor(max_workers=JOBS) as ex:
        futs = {ex.submit(push_chunk, lp, s, l, om, rp): (s, l) for (s, l, om) in tasks}
        for fu in cf.as_completed(futs):
            ok, info = fu.result()
            if not ok:
                ok_all = False
                say("   块失败: %s" % info)
            done += 1
            if done % 5 == 0 or done == len(tasks):
                el = time.time() - t0
                say("   进度 %d/%d  已传 %.1f/%.1f GB  %.1f MB/s"
                    % (done, len(tasks), done * CHUNK / 1e9, sz / 1e9, done * CHUNK / el / 1e6))
    say("   传完 %s  rc_all=%s  %.0fs" % (name, ok_all, time.time() - t0))

say("=== 全量 sha256 自证（166 端）===")
sc = "set -u\ncd '%s'\nfor f in Qwen3.8-Flash-Next-UD-IQ4_XS-0000[23]-of-00003.gguf; do echo \"$(stat -c '%%s %%n' $f)  sha256=$(sha256sum $f | cut -d' ' -f1)\"; done\ndf -h /models | tail -1\n" % RDIR
p = subprocess.run(SSH + ["bash -s"], input=sc.encode(), capture_output=True, timeout=1800)
say(p.stdout.decode("utf-8", "replace"))
if p.stderr.strip():
    say("ERR: " + p.stderr.decode("utf-8", "replace")[-300:])
say("期望: 00002 = c67b468b... / 00003 = 130560b6...")
say("DONE 总耗时 %.0fs" % (time.time() - t_all))
log.close()
