#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Emit the exact `docker run` that reproduces stratum166-407, from docker inspect."""
import json, subprocess, shlex

d = json.loads(subprocess.run(["docker", "inspect", "strata166-407"],
                              capture_output=True, text=True).stdout)[0]
h, c = d["HostConfig"], d["Config"]

print("### Config")
print("Cmd        :", c.get("Cmd"))
print("Entrypoint :", c.get("Entrypoint"))
print("WorkingDir :", c.get("WorkingDir"))
print("Image      :", c.get("Image"))
print("### HostConfig")
for k in ("NetworkMode", "IpcMode", "PidMode", "Privileged", "ShmSize", "RestartPolicy",
          "AutoRemove", "GroupAdd", "SecurityOpt", "CapAdd", "CapDrop", "ReadonlyRootfs"):
    print("%-13s: %s" % (k, h.get(k)))
print("Binds      :", h.get("Binds"))
print("Devices    :", [(x.get("PathOnHost"), x.get("PathInContainer")) for x in (h.get("Devices") or [])])
print("PortBindings:", h.get("PortBindings"))
print("Ulimits    :", h.get("Ulimits"))
print("Memory     :", h.get("Memory"), h.get("MemorySwap"))

args = ["docker", "run", "-d", "--name", "strata166-407"]
if h.get("RestartPolicy", {}).get("Name"):
    args += ["--restart", h["RestartPolicy"]["Name"]]
for b in h.get("Binds") or []:
    args += ["-v", b]
for dv in h.get("Devices") or []:
    args += ["--device", dv["PathOnHost"] + ":" + dv["PathInContainer"]]
for pb, binds in (h.get("PortBindings") or {}).items():
    for x in binds:
        args += ["-p", "%s:%s" % (x.get("HostPort"), pb.split("/")[0])]
for u in h.get("Ulimits") or []:
    args += ["--ulimit", "%s=%s:%s" % (u["Name"], u["Soft"], u["Hard"])]
for g in h.get("GroupAdd") or []:
    args += ["--group-add", g]
for s in h.get("SecurityOpt") or []:
    args += ["--security-opt", s]
if h.get("IpcMode") and h["IpcMode"] not in ("private", ""):
    args += ["--ipc", h["IpcMode"]]
if h.get("ShmSize"):
    args += ["--shm-size", str(h["ShmSize"])]
if h.get("NetworkMode") and h["NetworkMode"] not in ("default", "bridge"):
    args += ["--network", h["NetworkMode"]]
if h.get("Memory"):
    args += ["--memory", str(h["Memory"])]
args += ["--workdir", c.get("WorkingDir") or "/src"]
args += ["strata-gfx906:0.2.10-101"]
args += c.get("Cmd") or ["/bin/bash"]

print()
print("### 新容器命令")
print(" ".join(shlex.quote(a) for a in args))
