#!/usr/bin/env python3
"""patch release_check.py: add the 5th pointer (the llama.cpp pin).

Why this one exists: W1021 shipped "four pointers" and still could not answer
"which llama.cpp is the production engine built against".  The pin lives in five
places that can drift independently:

  upstream pin          .github/workflows/metal-build.yml  LLAMA_CPP_COMMIT
  what the image ships  /src/third_party/llama.cpp   (a whole tree, not a string)
  what the engine used STRATA_GGML_DIR at build time (here: /llama.cpp)
  what the binary says  debug paths "/llama.cpp/ggml/..."
  what the release says BUILD-IMAGE.json's llama_cpp field

Two of those are content, not labels: a tree can be swapped without touching any
version string, and a 7-char prefix cannot be checked against anything.  So the
check requires (a) a full 40-hex sha, (b) equality with the upstream pin, and
(c) equality with a *tree hash* computed inside the image.
"""
import io, re

P = "/home/albus/strata166/pr/strata-fork/ci/release_check.py"
s = io.open(P, encoding="utf-8").read()

# --- docstring: five pointers
s = s.replace('"""release_check -- the four pointers of a release, in one command (W1021).',
              '"""release_check -- the five pointers of a release, in one command (W1021, W1022).')

s = s.replace("""    compile-time define     -DSTRATA_VERSION in the build dir's cached command lines
""",
"""    compile-time define     -DSTRATA_VERSION in the build dir's cached command lines
    llama.cpp pin           upstream LLAMA_CPP_COMMIT == image's llama_cpp (40 hex) == the
                            tree actually present in the image (a tree hash, not a label)
""")

s = s.replace("""Every field must name the same engine version, and the container's image must be the one
the release claims.""",
"""Every field must name the same engine version, and the container's image must be the one
the release claims.  The llama.cpp pin is checked by *content*: a 7-char prefix proves
nothing, and an image can swap the vendored tree without changing any version string.""")

# --- new section before "if a.json:"
anchor = '    if a.json:\n'
new = '''    # 5. llama.cpp pin -- the dependency that decides quantisation and kernel behaviour
    pin_up = ""
    rc, wf = sh("grep -hoE 'LLAMA_CPP_COMMIT: *[0-9a-f]{40}' %s/.github/workflows/*.yml 2>/dev/null | head -1" % a.repo)
    m = re.search(r"[0-9a-f]{40}", wf or "")
    pin_up = m.group(0) if m else ""
    add("llama.cpp pin (upstream)", pin_up or "(not declared)",
        bool(pin_up), "the pin the fork's own CI builds against")

    pin_img = (meta.get("llama_cpp") or "").strip()
    full = bool(re.fullmatch(r"[0-9a-f]{40}", pin_img))
    add("llama.cpp pin (release)", pin_img or "(absent)",
        full and (not pin_up or pin_img == pin_up),
        "BUILD-IMAGE.json must carry the FULL 40-hex sha; a 7-char prefix cannot be verified")

    # a tree hash, because the vendored tree can be replaced without any string changing
    rc, th = sh(["docker", "exec", a.container, "sh", "-c",
                 "cd /src/third_party/llama.cpp && find . -type f -print0 | LC_ALL=C sort -z "
                 "| xargs -0 md5sum 2>/dev/null | md5sum | cut -d' ' -f1"], timeout=300)
    th_img = (meta.get("llama_cpp_tree") or "").strip()
    add("llama.cpp tree (image)", "%s claimed=%s" % (th.strip()[:12] or "?", th_img[:12] or "(absent)"),
        rc == 0 and bool(th_img) and th.strip() == th_img,
        "hash of the tree in the image must equal the one recorded at build time")

    # and the engine must have been compiled from that tree, not from a stale copy
    rc, n = sh("grep -c '/llama.cpp/' %s/_ci_all.txt 2>/dev/null" % a.build)
    n = int(re.sub(r"\\D", "", n or "0") or 0)
    add("llama.cpp in engine build", "%d references to /llama.cpp/" % n, n > 0,
        "STRATA_GGML_DIR must point at the vendored tree; 0 means the engine used something else")

'''
assert anchor in s
s = s.replace(anchor, new + anchor, 1)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("patched", len(s))
