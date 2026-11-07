set +e
echo "=== 工具位置 ==="
bash -lc 'command -v ninja; command -v cmake; command -v sudo'
echo "=== sudo 免密？ ==="
sudo -n true 2>&1 && echo SUDO_OK || echo SUDO_NO
echo
echo "=== 增量编译（cmake --build） ==="
cd /home/albus/strata166/src028/build-028r || exit 1
(sudo -n cmake --build . -j 2>&1 || cmake --build . -j 2>&1) | tail -30
echo "=== 产物 ==="
ls -l --time-style=+%H:%M strata
md5sum strata
