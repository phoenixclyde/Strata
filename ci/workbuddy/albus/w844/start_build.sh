set +e
chmod +x /home/albus/strata166/tmp/w844_build.sh 2>/dev/null
cp /home/albus/strata166/tmp/w844_build.sh /tmp/x 2>/dev/null
setsid nohup bash /home/albus/strata166/tmp/w844_build.sh >/dev/null 2>&1 &
sleep 3
echo "started; log tail:"
tail -5 /home/albus/strata166/data/w844_build.log 2>/dev/null
pgrep -af w844_build | head -2
