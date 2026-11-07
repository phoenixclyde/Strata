import subprocess, base64
def sh(s, t=900):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
docker run --rm --device /dev/kfd --device /dev/dri --group-add video --entrypoint bash strata-gfx906:0.2.4p4 -c '
cd /src/build-906 && ninja gfx906_gdn_rec_head >/tmp/b.log 2>&1
B=$(find /src/build-906 -maxdepth 2 -name "gfx906_gdn_rec_head" -type f | head -1)
for pp in 0 1 2; do
  echo "########## STRATA_GDN_PP=$pp ##########"
  STRATA_GDN_PP=$pp "$B" 2>&1 | grep -E "^FAIL|T 2048 variant|FAILURES" | head -8
done
' 2>&1 | tail -40
''', t=900))
