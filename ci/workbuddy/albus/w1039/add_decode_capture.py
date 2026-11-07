import io

p = "albus/w1039/window_kvg.sh"
s = io.open(p, encoding="utf-8").read()

# after arm A
a1 = 'python3 "$W/ab_kvg.py" "$W/arm_kvgA.json" A >> "$PROG" 2>&1 || fail "arm A failed"\n'
b1 = a1 + '''log "--- arm A decode breakdown (the CPU-expert segment is R104's second endpoint, P482) ---"
grep -a "strata decode timing:" "$LOG" | tail -1 | tee -a "$PROG"
'''
assert s.count(a1) == 1
s = s.replace(a1, b1, 1)

# after arm B
a2 = 'python3 "$W/ab_kvg.py" "$W/arm_kvgB.json" B >> "$PROG" 2>&1 || fail "arm B failed"\n'
b2 = a2 + '''log "--- arm B decode breakdown ---"
grep -a "strata decode timing:" "$LOG" | tail -1 | tee -a "$PROG"
'''
assert s.count(a2) == 1
s = s.replace(a2, b2, 1)

io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("window_kvg.sh: decode breakdown captured after both arms")
