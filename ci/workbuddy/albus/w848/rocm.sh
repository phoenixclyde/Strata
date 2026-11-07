set +e
echo "===== [1] 本机各镜像里的 ROCm 版本 ====="
for img in strata-gfx906:0.2.9 routek-base:gfx906-rocm101-hip716-torch215-tv030-df1 routek-vllm:0.28.0-gfx906-rocm721-devbase docker.1ms.run/mixa3607/llama.cpp-gfx906:v0.5.0-rocm-7.14; do
  echo "--- $img"
  docker image inspect "$img" >/dev/null 2>&1 || { echo "   (镜像不存在)"; continue; }
  docker run --rm --entrypoint bash "$img" -lc '
    for f in /opt/rocm/.info/version /opt/rocm/version /opt/rocm/.info/version-dev; do
      [ -f "$f" ] && echo "   $f: $(cat $f | head -1)"
    done
    command -v hipcc >/dev/null && echo "   hipcc: $(hipcc --version 2>/dev/null | grep -i "HIP version" | head -1)"
    ls /opt/rocm/lib/librocblas.so.* 2>/dev/null | head -2 | sed "s/^/   /"
    ls /opt/rocm*/lib/librocblas.so.* 2>/dev/null | head -3 | sed "s/^/   /"
  ' 2>&1 | head -8
done
echo
echo "===== [2] 当前生产镜像的 ROCm 细节 ====="
docker exec strata166-407 bash -lc 'cat /opt/rocm/.info/version 2>/dev/null; ls /opt/rocm | head -6; ls /opt/rocm/lib/librocblas.so.5.* 2>/dev/null | head -2; ls /opt/rocm/lib/rocblas/library/ 2>/dev/null | head -4'
echo
echo "===== [3] 本机全部镜像（找有没有更新的 gfx906 ROCm） ====="
docker images --format '{{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedSince}}' | grep -iE "rocm|gfx906|mixa|routek" | head -12
