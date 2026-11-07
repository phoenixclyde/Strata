import subprocess, base64
def sh(s, t=120):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
P=/home/albus/strata166/data/packs/huihui-ud-iq4_xs
ls -la "$P" | head -12
echo "=== manifest ==="
for f in "$P"/manifest.json "$P"/pack.json "$P"/index.json; do [ -f "$f" ] && { echo "-- $f"; head -c 900 "$f"; echo; }; done
echo "=== any json ==="
ls "$P"/*.json 2>/dev/null | head
'''))
