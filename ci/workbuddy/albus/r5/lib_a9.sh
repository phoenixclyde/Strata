#!/bin/bash
# lib_a9.sh —— AUDIT9 立的取证纪律（规则 S/T/U）的最小实现，所有新 A/B 脚本都应 source 它
#   用法：. /home/albus/strata166/tmp/lib_a9.sh
#         mark  OUT                    # 记 log 行号到 /tmp/.a9_mark
#         snap  OUT                    # 引擎真实 env（容器内取；宿主侧读不到 root 的 environ）
#         slice OUT                    # 把 marker 之后的新行按 pattern 追加到 OUT
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
LOG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
CONT=strata166-407

mark() { wc -l < "$LOG" > /tmp/.a9_mark; echo "  mark=$(cat /tmp/.a9_mark)" >> "$1"; }

snap() {
  echo "  envsnap(容器内):" >> "$1"
  docker exec "$CONT" bash -lc 'p=$(pgrep -f "build-906/strata --serve" | head -1); [ -n "$p" ] && tr "\0" "\n" < /proc/$p/environ | grep -E "^STRATA_" | sort || echo "NONE"' 2>/dev/null | sed 's/^/    /' >> "$1"
  python3 -c "import json;a=json.load(open('$CFG')).get('args');print('  args=%s' % [x for x in a if x.startswith('--conversation-cache') or x in ('256','4096')])" >> "$1"
}

slice() {   # $1=OUT $2=pattern
  local n0; n0=$(cat /tmp/.a9_mark)
  tail -n +$((n0 + 1)) "$LOG" | grep -a -E "$2" | cut -c1-160 | sed 's/^/  LOG /' >> "$1"
}
