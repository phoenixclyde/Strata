import subprocess, base64
def sh(s, t=90):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
docker run --rm --entrypoint bash strata-gfx906:0.2.4 -c 'grep -c "DNDEBUG" /src/build-906/build.ninja; grep -c "O3" /src/build-906/build.ninja; grep -m2 -o "FLAGS = .\{0,160\}" /src/build-906/build.ninja' 2>&1 | head -10
'''))
