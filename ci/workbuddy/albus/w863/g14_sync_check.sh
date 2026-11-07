#!/bin/bash
# 容器里的 /src（镜像内容）与我们的主线树是否一致？只比 serve/ 与 tool 层，全树太慢
R=/home/albus/strata166/pr/strata-fork
echo "=== is /src a mount or image content? ==="
docker inspect strata166-407 --format '{{range .Mounts}}{{.Destination}} <- {{.Source}}{{"\n"}}{{end}}'
echo
echo "=== compare serve/ : container /src vs our branch tree ==="
docker exec strata166-407 sh -c 'cd /src && find serve -type f -name "*.py" | sort | xargs md5sum' 2>/dev/null | sed 's#  # #' | awk '{print $1, $2}' | sort -k2 > /tmp/w863_ctr_serve.txt
cd "$R" && find serve -type f -name "*.py" | sort | xargs md5sum 2>/dev/null | awk '{print $1, $2}' | sort -k2 > /tmp/w863_host_serve.txt
echo "container files: $(wc -l < /tmp/w863_ctr_serve.txt)  host files: $(wc -l < /tmp/w863_host_serve.txt)"
echo "--- differences (empty = identical) ---"
diff /tmp/w863_ctr_serve.txt /tmp/w863_host_serve.txt | head -20
echo "--- count ---"
diff /tmp/w863_ctr_serve.txt /tmp/w863_host_serve.txt | grep -c '^[<>]'
echo
echo "=== engine binary actually in use ==="
docker exec strata166-407 md5sum /data/bin/strata-0.1.55h 2>/dev/null
echo
echo "=== disk space on 166 (for the unshallow) ==="
df -h /home | tail -1
du -sh /home/albus/strata166/pr/strata-fork/.git
