#!/bin/bash
echo "=== served app.css tail ==="
curl -s --max-time 8 http://127.0.0.1:8090/web/app.css | tail -3
echo "--- byte count ---"
curl -s --max-time 8 http://127.0.0.1:8090/web/app.css | wc -c
echo
echo "=== the three width rules as the browser sees them ==="
curl -s --max-time 8 http://127.0.0.1:8090/web/app.css | grep -nE "^\.(monitor|about|chat)[ ,{]|^\.monitor \{" | head -6
echo
echo "=== cache headers ==="
curl -sI --max-time 8 http://127.0.0.1:8090/web/app.css | tr -d '\r' | grep -iE "HTTP/|cache-control|etag|last-modified|content-length"
echo
echo "=== index.html inline width? (any max-width in the monitor section) ==="
curl -s --max-time 8 http://127.0.0.1:8090/ | grep -cE "max-width"
