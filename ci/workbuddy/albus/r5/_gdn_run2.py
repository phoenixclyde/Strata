import subprocess, base64
def sh(s, t=900):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
docker run --rm --device /dev/kfd --device /dev/dri --group-add video --entrypoint bash strata-gfx906:0.2.4p4 -c '
cd /src/build-906
ninja gfx906_gdn_rec_head >/tmp/b.log 2>&1; echo build_rc=$?
B=$(find /src/build-906 -maxdepth 2 -name "gfx906_gdn_rec_head" -type f | head -1); echo BIN=$B
echo "=== run ==="
"$B" 2>&1 | tail -30
echo "run_rc=$?"
' 2>&1 | tail -34
''', t=900))
