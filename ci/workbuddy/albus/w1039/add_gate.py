import io

p = "albus/w1039/window_kvg.sh"
s = io.open(p, encoding="utf-8").read()

old = 'startup_notes\n\n'
new = '''startup_notes

# HARD GATE (W1039, P478): kvg.on is a condition SEPARATE from the eleven that enable the elastic K/V
# (generate.cpp:9961 also needs xcache.vmm_range(), d_res, host_res, srcp and top > floor).  When it is false the
# elastic K/V is still on but kvg_ensure returns true WITHOUT growing ("if (!kvg.on || cells <= kvg.cells) return true"),
# so a long request would walk into unmapped VA.  Nothing long is sent until the line that proves growth is armed.
if ! grep -aq "elastic K/V:" "$LOG"; then
  log "ABORT: no 'elastic K/V:' line at start-up - kvg.on is false; generate.cpp's own warning follows"
  grep -a "kv-grow is off" "$LOG" | tail -2 | tee -a "$PROG"
  fail "refusing to send a 20K request into an elastic K/V that cannot grow"
fi
log "elastic K/V line present -> the growth path is armed"

'''
assert s.count(old) == 1, s.count(old)
io.open(p, "w", encoding="utf-8", newline="\n").write(s.replace(old, new, 1))
print("window_kvg.sh: hard gate inserted")
