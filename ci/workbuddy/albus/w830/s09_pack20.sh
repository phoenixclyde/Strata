cd /home/albus/strata166
cat > /tmp/lost20.txt <<'EOF'
CMakeLists.txt
README.md
docs/INSTALL.md
include/strata/dsv41/exl3.hpp
metal/CMakeLists.txt
metal/src/gpu/runtime.cpp
metal/src/mtl_rt.h
metal/src/mtl_rt.mm
packaging/UPDATES.md
setup.py
src/dsv41/ds4_gguf.cu
src/dsv41/ds4_iq.cu
src/dsv41/ds4_iq.cuh
src/dsv41/ds4_model.cu
strata_cli/cli.py
strata_cli/launch/runner.py
strata_control/doctor.py
strata_control/updater.py
tests/terminal/test_launch.py
tests/terminal/test_tui2_023_versions.py
EOF
rm -rf /tmp/lost20 && mkdir -p /tmp/lost20
while read -r f; do
  [ -f "src0271/$f" ] || continue
  mkdir -p "/tmp/lost20/$(dirname "$f")"
  cp "src0271/$f" "/tmp/lost20/$f"
done < /tmp/lost20.txt
cd /tmp/lost20 && tar czf /tmp/lost20.tgz . && ls -la /tmp/lost20.tgz
