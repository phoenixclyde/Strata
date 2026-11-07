# 新镜像指纹 + 建 404 容器（只读 + create，不启动）
import subprocess, base64, time

OUT = r"D:/workbuddy_space/strata_ws/deploy/tmp/_w712_image404.out.txt"
f = open(OUT, "w", encoding="utf-8")
def log(s):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), s)
    print(line); f.write(line + "\n"); f.flush()

def run_remote(script, timeout=300):
    assert "\r" not in script
    b64 = base64.b64encode(script.encode("utf-8")).decode("ascii")
    p = subprocess.run(
        ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
         "albus@192.168.50.166", "base64 -d | bash"],
        input=(b64 + "\n").encode("ascii"), capture_output=True, timeout=timeout)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")

script = r"""
set -u
echo "== image digest / size =="
docker images --digests --format '{{.Repository}}:{{.Tag}} | {{.Digest}} | {{.ID}} | {{.Size}}' | grep -i strata
echo "== engine binary in image =="
docker run --rm --entrypoint bash strata-gfx906:0.1.40.4 -lc 'ls -l /src/build-906/strata; md5sum /src/build-906/strata; grep -n "project(strata VERSION" /src/CMakeLists.txt; grep -c "cudaEventBlockingSync hipEventBlockingSync" /src/include/strata/platform/hip_compat/strata_hip.h; grep -n "STRATA_Q6K_EXPERTS OR STRATA_HIP_GFX906" /src/CMakeLists.txt'
echo "== create container strata166-404 =="
if docker inspect strata166-404 >/dev/null 2>&1; then
  docker inspect -f 'exists: status={{.State.Status}} image={{.Config.Image}}' strata166-404
else
  docker create --name strata166-404 \
    --restart unless-stopped \
    --device=/dev/kfd --device=/dev/dri --group-add video \
    --ipc=host --ulimit memlock=-1 \
    -e HSA_OVERRIDE_GFX_VERSION=9.0.6 \
    -p 8090:8090 \
    -v /home/albus/strata166/data:/data \
    -v /home/albus/strata166/weights:/weights:ro \
    strata-gfx906:0.1.40.4 \
    bash -lc 'cd /src && exec python3 serve/server.py --engine strata --config /data/strata-ud-iq4_xs.json --port 8090'
  docker inspect strata166-404 --format 'created: status={{.State.Status}} image={{.Config.Image}} Binds={{json .HostConfig.Binds}} Ports={{json .HostConfig.PortBindings}} RAS={{json .HostConfig.RestartPolicy}} Dev={{json .HostConfig.Devices}}'
fi
echo "== containers =="
docker ps -a --filter name=strata --format '{{.Names}} | {{.Status}} | {{.Image}}'
echo IMG_DONE
"""
rc, out, err = run_remote(script, timeout=300)
log("image/create rc=%d" % rc)
f.write(out + "\n")
if err.strip():
    f.write("STDERR:\n" + err + "\n")
f.close()
print(out)
print("STDERR:", err[-600:])
