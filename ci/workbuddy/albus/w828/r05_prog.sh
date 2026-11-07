echo "--- build progress ---"
tail -3 /home/albus/strata166/src028/build-028.log 2>/dev/null
echo "lines: $(wc -l < /home/albus/strata166/src028/build-028.log 2>/dev/null)"
docker ps --format '{{.Names}} {{.Status}}' | grep buildrun || echo "build container gone"
echo "--- image /src layout ---"
docker run --rm strata-gfx906:0.2.4p4 bash -lc 'ls /src | head -20; echo ---; ls /src/serve 2>/dev/null | head; echo ---; python3 -c "import sys; print(sys.version)"'
echo "--- container mounts ---"
docker inspect strata166-407 --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}
{{end}}'
echo "--- mem ---"
free -g | head -2
