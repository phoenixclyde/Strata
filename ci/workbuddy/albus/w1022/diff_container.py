#!/usr/bin/env python3
"""Diff the run parameters of the live container against the pre-rebuild one.

Rebuilding a container from a remembered command line is how a flag goes missing: the
record said "ulimit -l unlimited" (a result), not "--ulimit memlock=-1:-1" (the flag).
This dumps HostConfig from both and prints only what differs.
"""
import json, subprocess, sys

NEW, OLD = "strata166-407", "strata166-407-old"
KEYS = ["Binds", "PortBindings", "RestartPolicy", "Devices", "GroupAdd", "SecurityOpt",
        "ShmSize", "IpcMode", "Ulimits", "Memory", "MemorySwap", "NanoCpus", "CapAdd",
        "Privileged", "NetworkMode", "LogConfig", "ReadonlyRootfs", "PidMode"]


def hc(name):
    r = subprocess.run(["docker", "inspect", "-f", "{{json .HostConfig}}", name],
                       capture_output=True, text=True)
    return json.loads(r.stdout)


a, b = hc(NEW), hc(OLD)
diff = 0
for k in KEYS:
    if json.dumps(a.get(k), sort_keys=True) != json.dumps(b.get(k), sort_keys=True):
        diff += 1
        print("DIFF %-14s new=%s\n                old=%s" % (k, json.dumps(a.get(k)), json.dumps(b.get(k))))
print("hostconfig differences: %d (compared %d keys)" % (diff, len(KEYS)))

# mounts are separate from HostConfig
ma = subprocess.run(["docker", "inspect", "-f", "{{json .Mounts}}", NEW], capture_output=True, text=True).stdout
mb = subprocess.run(["docker", "inspect", "-f", "{{json .Mounts}}", OLD], capture_output=True, text=True).stdout
na = sorted((m["Source"], m["Destination"], m.get("Mode", "")) for m in json.loads(ma))
nb = sorted((m["Source"], m["Destination"], m.get("Mode", "")) for m in json.loads(mb))
print("mounts equal:", na == nb)
for x in na:
    print("  new:", x)
sys.exit(0)
