set +e
D=/home/albus/strata166/gfx029
echo "===== [1] 遥测/引擎是否依赖 rocm-smi（10.1 已移除，改用 amd-smi）====="
grep -rn "rocm-smi\|rocm_smi\|amd-smi\|amd_smi" "$D/serve" "$D/src" "$D/strata_control" 2>/dev/null | head -12
echo
echo "===== [2] 两个镜像里 rocm-smi / amd-smi 是否存在 ====="
for img in strata-gfx906:0.2.9t2 strata-gfx906:0.2.9r1; do
  echo "--- $img"
  docker run --rm --entrypoint bash "$img" -lc 'for c in rocm-smi amd-smi rocminfo; do printf "  %-10s " $c; command -v $c || echo "(无)"; done; ls /opt/rocm/bin/*smi* 2>/dev/null | head -3'
done
echo
echo "===== [3] 遥测数据来源（我们补丁读的是哪） ====="
grep -n "gpu_pcie\|/sys/class/drm\|hwmon" "$D/serve/telemetry.py" | head -10
