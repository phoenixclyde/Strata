import io

# 1) summarize_kvg.py: accept several files per arm (A1 A2 -- B1 B2), pooling the repetitions
p = "albus/w1039/summarize_kvg.py"
s = io.open(p, encoding="utf-8").read()

old_main = '''    a, b = load(sys.argv[1]), load(sys.argv[2])
    pa, pb = per_target(a), per_target(b)'''
new_main = '''    args = sys.argv[1:]
    if "--" in args:
        k = args.index("--")
        fa, fb = args[:k], args[k + 1:]
    else:
        fa, fb = [args[0]], [args[1]]
    arms_a = [load(f) for f in fa]
    arms_b = [load(f) for f in fb]

    def pool(arms):
        out = {}
        for d in arms:
            for t, xs in per_target(d).items():
                out.setdefault(t, []).extend(xs)
        return out

    pa, pb = pool(arms_a), pool(arms_b)'''
assert old_main in s
s = s.replace(old_main, new_main, 1)

old_dec = '''    da = [x["tok_s"] for x in a.get("decode", [])]
    db = [x["tok_s"] for x in b.get("decode", [])]'''
new_dec = '''    da = [x["tok_s"] for d in arms_a for x in d.get("decode", [])]
    db = [x["tok_s"] for d in arms_b for x in d.get("decode", [])]'''
assert old_dec in s
s = s.replace(old_dec, new_dec, 1)
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("summarize_kvg.py: multi-file arms (A1 A2 -- B1 B2)")

# 2) window_kvg.sh: two passes per arm, so every target has n=4
w = "albus/w1039/window_kvg.sh"
t = io.open(w, encoding="utf-8").read()

a1 = 'python3 "$W/ab_kvg.py" "$W/arm_kvgA.json" A >> "$PROG" 2>&1 || fail "arm A failed"\n'
b1 = (a1 +
      'date +%s%N > "$W/salt"\n'
      'log "=== arm A pass 2 (same arm, fresh salt: n=4 per target) ==="\n'
      'python3 "$W/ab_kvg.py" "$W/arm_kvgA2.json" A2 >> "$PROG" 2>&1 || fail "arm A pass 2 failed"\n')
assert t.count(a1) == 1
t = t.replace(a1, b1, 1)

a2 = 'python3 "$W/ab_kvg.py" "$W/arm_kvgB.json" B >> "$PROG" 2>&1 || fail "arm B failed"\n'
b2 = (a2 +
      'date +%s%N > "$W/salt"\n'
      'log "=== arm B pass 2 ==="\n'
      'python3 "$W/ab_kvg.py" "$W/arm_kvgB2.json" B2 >> "$PROG" 2>&1 || fail "arm B pass 2 failed"\n'
      'log "=== verdict ==="\n'
      'python3 "$W/summarize_kvg.py" "$W/arm_kvgA.json" "$W/arm_kvgA2.json" -- '
      '"$W/arm_kvgB.json" "$W/arm_kvgB2.json" >> "$PROG" 2>&1 || log "WARN summarize failed"\n'
      'tail -20 "$PROG"\n')
assert t.count(a2) == 1
t = t.replace(a2, b2, 1)
io.open(w, "w", encoding="utf-8", newline="\n").write(t)
print("window_kvg.sh: 2 passes per arm + inline verdict")
