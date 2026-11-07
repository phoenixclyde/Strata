#!/bin/bash
set -u
W=/home/albus/strata166/work/r77
echo "=== 1) server.py 语法检查 ==="
python3 -m py_compile $W/serve/server.py && echo "SYNTAX OK"
echo "--- 新增函数是否在 ---"
grep -c "_raise_if_fatal_gpu" $W/serve/server.py
grep -c "_note_fatal_gpu_exit" $W/serve/server.py
grep -c "FATAL_GPU_MAX" $W/serve/server.py

echo
echo "=== 2) 容器内 server.py 现状 ==="
docker exec strata166-407 md5sum /src/serve/server.py
echo "--- 仓库原版 md5（应相同）---"
md5sum /home/albus/strata166/pr/strata-fork/serve/server.py

echo
echo "=== 3) 引擎 env 如何传（server.py 里的 env 构造）==="
grep -n "env = \|env=env\|merged_env\|os.environ.copy" $W/serve/server.py | head -10

echo
echo "=== 4) 容器内 python 能否编译新 server.py（拷到 /tmp 试编）==="
docker cp $W/serve/server.py strata166-407:/tmp/server_new.py >/dev/null 2>&1
docker exec strata166-407 bash -lc 'cd /tmp && python3 -m py_compile server_new.py && echo "CONTAINER SYNTAX OK"; python3 -c "print(1)"'
