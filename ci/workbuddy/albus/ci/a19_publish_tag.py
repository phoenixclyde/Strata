# -*- coding: utf-8 -*-
"""publish.py: also report the tag HEAD points at.

Rationale (AUDIT18/A2): the discipline is "production runs a tagged commit". The commit status
is the one place GitHub can see that, so it must carry the tag -- a bare exe name cannot prove it.
"""
p = r"D:\workbuddy_space\strata_ws\albus\ci\publish.py"
s = open(p, encoding="utf-8").read()

old_line = "  'bench_tag':b.get('git_tag')}))\\n\""
new_line = ("  'bench_tag':b.get('git_tag'),\n"
            "  'head_tag':subprocess.run(['git','-C','/home/albus/strata166/pr/strata-fork',\n"
            "     'describe','--exact-match','--tags','HEAD'],capture_output=True,text=True).stdout.strip() or None}))\\n\"")

if "head_tag" in s:
    print("already patched")
else:
    assert s.count(old_line) == 1, s.count(old_line)
    s = s.replace(old_line, new_line, 1)

    old_print = 'print("source : exe=%s  bench=%s  tag=%s" % (s["exe"], s["bench_run"], s["bench_tag"]))'
    new_print = ('print("source : exe=%s  bench=%s  bench_tag=%s  head_tag=%s"\n'
                 '          % (s["exe"], s["bench_run"], s["bench_tag"], s.get("head_tag")))')
    assert s.count(old_print) == 1
    s = s.replace(old_print, new_print, 1)

    old_desc = '''                         s["env"], "ok" if s["ok"] and s["loaded"] else "NOT OK"))'''
    new_desc = '''                         s["env"], "ok" if s["ok"] and s["loaded"] else "NOT OK")
                      + (" · " + s["head_tag"] if s.get("head_tag") else " · UNTAGGED"))'''
    assert s.count(old_desc) == 1
    s = s.replace(old_desc, new_desc, 1)

    open(p, "w", encoding="utf-8", newline="\n").write(s)
    print("publish.py patched (head_tag)")
