cd /home/albus/strata166/src028
echo "=== sh_stream_on() ==="
sed -n '330,365p' src/core/verify.cpp
echo "=== sh_cs_ creation ==="
grep -n "sh_cs_" src/core/verify.cpp | head -12
echo "=== arch_defaults tables: which archs set SH_STREAM ==="
sed -n '55,100p' src/core/arch_defaults.cpp
echo "=== HIP default note in docs/AMD_HIP.md ==="
grep -n -B3 -A6 "SH_STREAM" docs/AMD_HIP.md | head -40
