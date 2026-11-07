import subprocess, base64
def sh(s, t=600):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
docker run --rm --entrypoint bash strata-gfx906:0.2.4p4 -c '
ls -l /src/build-906/tests/gfx906_gdn_rec_head 2>/dev/null || find /src/build-906 -name "*gdn_rec_head*" -type f 2>/dev/null | head -3
' 2>&1 | head -6
''', t=300))
