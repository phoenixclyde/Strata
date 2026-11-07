echo "=== images ==="
docker images | grep -Ei 'strata|rocm|hip' | head -8
echo
echo "=== which image has the build toolchain? ==="
for img in $(docker images --format '{{.Repository}}:{{.Tag}}' | grep -Ei 'strata-gfx906' | head -4); do
  printf '  %-28s ' "$img"
  docker run --rm "$img" bash -lc 'command -v cmake >/dev/null && command -v ninja >/dev/null && echo "cmake+ninja OK ($(cmake --version|head -1))" || echo "no tools"' 2>/dev/null | head -1
done
