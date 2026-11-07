L=/home/albus/strata166/src028/build-028w.log
tail -3 $L
grep -c 'error:' $L || true
ls -la /home/albus/strata166/src028/build-028w/strata
grep -o 'STRATA_VERIFY_MAX_T=[0-9]*' /home/albus/strata166/src028/build-028w/build.ninja | sort -u
cp -f /home/albus/strata166/src028/build-028w/strata /home/albus/strata166/data/bin/strata-0.1.54w
chmod 755 /home/albus/strata166/data/bin/strata-0.1.54w
docker run --rm -v /home/albus/strata166/data:/data strata-gfx906:0.2.4p4 /data/bin/strata-0.1.54w --version
strings /home/albus/strata166/data/bin/strata-0.1.54w | grep -c 'moe_grouped_s2_wide' || true
ls -la /home/albus/strata166/data/bin/
