set +e
docker inspect strata166-407 --format 'started={{.State.StartedAt}} restarts={{.RestartCount}}'
md5sum /home/albus/strata166/data/bin/strata-0.1.55g
md5sum /home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
ls -l --time-style=+%H:%M /home/albus/strata166/data/bin/ | tail -4
