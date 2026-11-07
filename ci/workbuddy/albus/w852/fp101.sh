set +e
C=strata166-407
echo "image_id=$(docker image inspect strata-gfx906:0.2.9-101 --format '{{.Id}}')"
echo "image_size=$(docker image inspect strata-gfx906:0.2.9-101 --format '{{.Size}}')"
echo "started=$(docker inspect $C --format '{{.State.StartedAt}}')"
echo "container_id=$(docker inspect $C --format '{{.Id}}')"
echo "exe_md5=$(md5sum /home/albus/strata166/data/bin/strata-0.1.55g | cut -d' ' -f1)"
echo "cfg_md5=$(md5sum /home/albus/strata166/data/strata-huihui-ud-iq4_xs.json | cut -d' ' -f1)"
echo "table_md5=$(md5sum /home/albus/strata166/data/gfx906-rocblas-5.7.0.txt | cut -d' ' -f1)"
echo "table_rows=$(grep -c '^f16o' /home/albus/strata166/data/gfx906-rocblas-5.7.0.txt)"
