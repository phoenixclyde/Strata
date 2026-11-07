import subprocess, base64
def sh(s, t=90):
    p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10","albus@192.168.50.166","base64 -d | bash"],
                       input=base64.b64encode(s.encode()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=t)
    return p.stdout.decode("utf-8","replace")
print(sh(r'''
echo "=== opt flags in build.ninja (old image, container down -> use image) ==="
docker run --rm --entrypoint sh strata-gfx906:0.2.4 -c 'grep -o -- "-O[0-9s]" /src/build-906/build.ninja | sort | uniq -c; echo ---; grep -o -- "--offload-arch=[a-z0-9]*" /src/build-906/build.ninja | sort -u; echo ---; grep -c "max-ilp" /src/build-906/build.ninja' 2>&1 | head -12
echo "=== build type ==="
docker run --rm --entrypoint sh strata-gfx906:0.2.4 -c 'grep -E "^CMAKE_BUILD_TYPE|^CMAKE_HIP_FLAGS" /src/build-906/CMakeCache.txt' 2>&1
'''))
