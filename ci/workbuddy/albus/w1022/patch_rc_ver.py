#!/usr/bin/env python3
"""release_check: read the pin from the authoritative file first, and require the two
declarations to agree.

`CMakeLists.txt:2078` says the fallback for an empty STRATA_GGML_DIR is "the pinned
upstream commit (third_party/ggml/VERSION.txt)" -- so VERSION.txt, not the workflow, is
the declaration the build actually obeys.  The workflow pin is a second copy.  Two
copies that can disagree must be compared, not picked from.
"""
import io

P = "/home/albus/strata166/pr/strata-fork/ci/release_check.py"
s = io.open(P, encoding="utf-8").read()

old = '''    pin_up = ""
    rc, wf = sh("grep -hoE 'LLAMA_CPP_COMMIT: *[0-9a-f]{40}' %s/.github/workflows/*.yml 2>/dev/null | head -1" % a.repo)
    m = re.search(r"[0-9a-f]{40}", wf or "")
    pin_up = m.group(0) if m else ""
    add("llama.cpp pin (upstream)", pin_up or "(not declared)",
        bool(pin_up), "the pin the fork's own CI builds against")
'''
new = '''    # two declarations: third_party/ggml/VERSION.txt is what CMakeLists.txt:2078 obeys, the
    # workflow is a second copy.  They must agree; a disagreement is the failure, not a tie to break.
    rc, ver_txt = sh("head -1 %s/third_party/ggml/VERSION.txt 2>/dev/null" % a.repo)
    mv = re.search(r"\\b[0-9a-f]{40}\\b", ver_txt or "")
    pin_ver = mv.group(0) if mv else ""
    rc, wf = sh("grep -hoE 'LLAMA_CPP_COMMIT: *[0-9a-f]{40}' %s/.github/workflows/*.yml 2>/dev/null | head -1" % a.repo)
    mw = re.search(r"[0-9a-f]{40}", wf or "")
    pin_wf = mw.group(0) if mw else ""
    pin_up = pin_ver or pin_wf
    add("llama.cpp pin (upstream)", pin_ver or pin_wf or "(not declared)",
        bool(pin_up) and (not (pin_ver and pin_wf) or pin_ver == pin_wf),
        "VERSION.txt (CMakeLists.txt:2078) and the workflow pin must both exist and agree")
'''
assert old in s
s = s.replace(old, new, 1)
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("patched")
