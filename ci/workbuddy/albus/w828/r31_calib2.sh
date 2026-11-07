set -e
cd /home/albus/strata166
docker rm -f w828calib >/dev/null 2>&1 || true
rm -f /home/albus/strata166/data/w828_calib.out
docker run -d --name w828calib --ipc host --security-opt label=disable \
  --device=/dev/kfd --device=/dev/dri --group-add video \
  -v /home/albus/strata166/src028:/src -v /home/albus/strata166/data:/data \
  -v /models:/models:ro \
  -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_SRC=/src \
  -w /src strata-gfx906:0.2.8 \
  bash -lc 'python3 tools/calibrate.py /data/w828_calib.json > /data/w828_calib.out 2>&1; echo EXIT=$? >> /data/w828_calib.out' >/dev/null
sleep 25
docker ps --format '{{.Names}} {{.Status}}' | grep w828calib || echo "CALIB GONE"
echo "--- out ---"
tail -14 /home/albus/strata166/data/w828_calib.out 2>/dev/null | cut -c1-180
