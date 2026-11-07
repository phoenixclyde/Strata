echo "load: $(cat /proc/loadavg)"
docker top buildrun028 -eo pid,etime,pcpu,rss,args 2>/dev/null | grep -E 'clang|ninja' | head -12 | cut -c1-190
echo "--- last ninja lines ---"
tail -6 /home/albus/strata166/src028/build-028.log
echo "--- mem ---"
free -g | head -2
