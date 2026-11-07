#!/bin/bash
echo "=== GET headers for app.css ==="
curl -s -D - -o /dev/null --max-time 8 http://127.0.0.1:8090/web/app.css | tr -d '\r' | sed '/^$/d'
echo
echo "=== index.html headers ==="
curl -s -D - -o /dev/null --max-time 8 http://127.0.0.1:8090/ | tr -d '\r' | head -8
