import io
p = "/home/albus/strata166/pr/strata-fork/ci/selftest_pin.py"
s = io.open(p, encoding="utf-8").read()
old = '''    if ver:
        # CMakeLists.txt:2078 obeys this file, so it is the first declaration
'''
new = '''    # The release pin row reads the recipe when there is no image (--offline), so a complete
    # fixture needs one: without it every case reported "llama.cpp pin (release) (absent)" and
    # the baseline could not pass -- the same "fixture is not the real thing" shape again.
    os.makedirs(os.path.join(tmp, "ci", "docker"), exist_ok=True)
    io.open(os.path.join(tmp, "ci", "docker", "Dockerfile-selftest"), "w",
            encoding="utf-8").write("ENV LLAMA_CPP_SHA=%s\\n" % SHA)
    if ver:
        # CMakeLists.txt:2078 obeys this file, so it is the first declaration
'''
assert old in s, "fixture anchor"
io.open(p, "w", encoding="utf-8", newline="\n").write(s.replace(old, new, 1))
print("fixture: dockerfile with the pin")
