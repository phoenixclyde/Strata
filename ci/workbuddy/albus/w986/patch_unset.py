import io

p = "ci/cfg_apply.py"
s = io.open(p, encoding="utf-8").read()

if "--unset-env" not in s:
    s = s.replace('    ap.add_argument("--env", action="append", default=[], help="KEY=VALUE (env dict)")',
                  '    ap.add_argument("--env", action="append", default=[], help="KEY=VALUE (env dict)")\n'
                  '    ap.add_argument("--unset-env", action="append", default=[], help="KEY to delete from env")\n'
                  '    ap.add_argument("--unset-arg", action="append", default=[], help="FLAG to delete from args (with its value)")',
                  1)

    # apply_sets signature + body
    s = s.replace("def apply_sets(cfg, sets, envs):", "def apply_sets(cfg, sets, envs, unsets=(), unset_args=()):", 1)
    s = s.replace('''    for s in envs:
        if "=" not in s:
            raise SystemExit("--env wants KEY=VALUE, got %r" % s)
        k, v = s.split("=", 1)
        env[k] = v
    return cfg''',
                  '''    for s in envs:
        if "=" not in s:
            raise SystemExit("--env wants KEY=VALUE, got %r" % s)
        k, v = s.split("=", 1)
        env[k] = v
    for k in unsets:
        env.pop(k, None)
    for f in unset_args:
        flag = f if f.startswith("--") else "--" + f
        while flag in cfg["args"]:
            i = cfg["args"].index(flag)
            del cfg["args"][i]
            if i < len(cfg["args"]) and not str(cfg["args"][i]).startswith("--"):
                del cfg["args"][i]
    return cfg''', 1)

    s = s.replace("cand = apply_sets(copy.deepcopy(live), a.set, a.env)",
                  "cand = apply_sets(copy.deepcopy(live), a.set, a.env, a.unset_env, a.unset_arg)", 1)

    # report deletions in the delta print
    s = s.replace('''    print("   env  deltas: %s" % (env_changed or "none"))''',
                  '''    print("   env  deltas: %s" % (env_changed or "none"))
    gone = [k for k in live.get("env", {}) if k not in cand["env"]]
    gone_args = [x for x in live["args"] if x.startswith("--") and x not in cand["args"]]
    print("   removed: env %s | args %s" % (gone or "none", gone_args or "none"))''', 1)

io.open(p, "w", encoding="utf-8").write(s)
print("patched --unset-env / --unset-arg")
