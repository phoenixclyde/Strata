import subprocess, sys, os, io

HOST = "albus@192.168.50.166"
SSH = r"C:\Windows\System32\OpenSSH\ssh.exe"
if not os.path.isfile(SSH):
    SSH = "ssh"

def run(cmd, inp=None, timeout=180):
    r = subprocess.run([SSH, "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
                        "-o", "StrictHostKeyChecking=accept-new", HOST, cmd],
                       input=inp, capture_output=True, timeout=timeout)
    return r.returncode, r.stdout.decode("utf-8", "replace"), r.stderr.decode("utf-8", "replace")

def push(local, remote):
    data = io.open(local, "rb").read()
    rc, out, err = run("cat > %s" % remote, inp=data)
    if rc != 0:
        raise SystemExit("push fail %s %s" % (out, err))

if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "push":
        for f in sys.argv[2:]:
            push(f, "/tmp/" + os.path.basename(f))
            print("pushed", f)
    elif mode == "run":
        script = sys.argv[2]
        outfile = sys.argv[3] if len(sys.argv) > 3 else "out.txt"
        push(script, "/tmp/_run.sh")
        rc, out, err = run("bash /tmp/_run.sh", timeout=300)
        txt = "RC=%d\n=== STDOUT ===\n%s\n=== STDERR ===\n%s" % (rc, out, err)
        io.open(outfile, "w", encoding="utf-8").write(txt)
        print(txt[:8000])
    elif mode == "runpy":
        script = sys.argv[2]
        outfile = sys.argv[3] if len(sys.argv) > 3 else "out.txt"
        push(script, "/tmp/_run.py")
        rc, out, err = run("python3 /tmp/_run.py", timeout=300)
        txt = "RC=%d\n=== STDOUT ===\n%s\n=== STDERR ===\n%s" % (rc, out, err)
        io.open(outfile, "w", encoding="utf-8").write(txt)
        print(txt[:8000])
