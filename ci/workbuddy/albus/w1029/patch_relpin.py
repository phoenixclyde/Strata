import io
p = "/home/albus/strata166/pr/strata-fork/ci/release_check.py"
s = io.open(p, encoding="utf-8").read()
old = '''    pin_img = (meta.get("llama_cpp") or "").strip()
    full = bool(re.fullmatch(r"[0-9a-f]{40}", pin_img))
    add("llama.cpp pin (release)", pin_img or "(absent)",
        full and (not pin_up or pin_img == pin_up),
        "BUILD-IMAGE.json must carry the FULL 40-hex sha; a 7-char prefix cannot be verified")
'''
new = '''    pin_img = (meta.get("llama_cpp") or "").strip()
    if a.offline:
        # The image is not on a runner, but its recipe is in the repo: ci/docker/Dockerfile-*
        # declares the pin it bakes in.  Judging that declaration is what a static run can do
        # honestly; the built copy is what the skipped BUILD-IMAGE.json row is for.
        rc, df = sh("grep -hoE 'LLAMA_CPP_SHA=[0-9a-f]{40}' %s/ci/docker/Dockerfile-* 2>/dev/null | head -1" % a.repo)
        md = re.search(r"[0-9a-f]{40}", df or "")
        pin_img = md.group(0) if md else ""
    full = bool(re.fullmatch(r"[0-9a-f]{40}", pin_img))
    add("llama.cpp pin (release)", pin_img or "(absent)",
        full and (not pin_up or pin_img == pin_up),
        "BUILD-IMAGE.json (offline: ci/docker/Dockerfile-*) must carry the FULL 40-hex sha")
'''
assert old in s, "relpin anchor"
io.open(p, "w", encoding="utf-8", newline="\n").write(s.replace(old, new, 1))
print("release pin: dockerfile fallback")
