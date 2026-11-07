import subprocess, base64, os
def sh(s, t=180):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
files = """r0_results_20261025_135559.txt r5_ab_20261025_151632.txt r5_pf_20261025_150625.txt
w792_adopt_20261025_153424.txt w792_prodchk.txt w793_ab_20261025_161311.txt w793b_ab_20261025_161914.txt
w794_ab_20261025_165037.txt w794_ab_20261025_165419.txt w794_ab_20261025_170321.txt w794_final_20261025_170358.txt
w795_ab_20261025_173232.txt w795j_ab_20261025_175252.txt""".split()
out = r"D:/workbuddy_space/strata_ws/albus/audit8/data"
for f in files:
    b64 = sh("base64 -w0 /home/albus/strata166/data/" + f)
    try:
        raw = base64.b64decode(b64)
        open(os.path.join(out, f), "wb").write(raw)
        print(f, len(raw))
    except Exception as e:
        print(f, "FAIL", e, b64[:80])
