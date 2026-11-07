set +e
docker inspect strata166-407 --format 'started={{.State.StartedAt}} restarts={{.RestartCount}}'
md5sum /home/albus/strata166/data/bin/strata-0.1.54n4
md5sum /home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
docker inspect strata166-407 --format '{{.Image}}'
ls -l --time-style=+%H:%M /home/albus/strata166/data/bin/strata-0.1.54n4
