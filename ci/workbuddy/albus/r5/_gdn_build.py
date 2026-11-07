import subprocess, base64
def sh(s, t=900):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
docker run --rm --device /dev/kfd --device /dev/dri --group-add video --entrypoint bash strata-gfx906:0.2.4p4 -c '
cd /src/build-906
echo "=== build $(date +%H:%M:%S) ==="
ninja gfx906_gdn_rec_head 2>&1 | tail -6
echo "=== run $(date +%H:%M:%S) ==="
./tests/gfx906_gdn_rec_head 2>&1 | tail -25
echo "rc=$?"
' 2>&1 | tail -40
''', t=900))
