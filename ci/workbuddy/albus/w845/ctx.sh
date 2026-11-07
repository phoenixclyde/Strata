set +e
L=/data/strata-huihui-ud-iq4_xs.log
echo "===== [1] unknown argument: 256 的上下文（第 37001 行附近） ====="
docker exec strata166-407 bash -lc "sed -n '36992,37006p' $L"
echo
echo "===== [2] 它出现多少次、最早最晚的行号 ====="
docker exec strata166-407 bash -lc "grep -an 'unknown argument: 256' $L | head -3; echo ...; grep -an 'unknown argument: 256' $L | tail -3; echo -n 'total='; grep -ac 'unknown argument: 256' $L"
echo
echo "===== [3] 0.1.54 那次 session 的上下文（77118 前后 12 行） ====="
docker exec strata166-407 bash -lc "sed -n '77106,77124p' $L"
echo
echo "===== [4] 三次 session is up 的间隔线索：各自的 loading/slots 行 ====="
docker exec strata166-407 bash -lc "grep -an 'loading the experts\|slots ready\|warm' $L | tail -6"
