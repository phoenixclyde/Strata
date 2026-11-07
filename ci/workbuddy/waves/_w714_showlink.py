# 展示用：把 166 上相关目录的文件列表原样抓回（远端只输出原始 ls / readlink，本地渲染）
import base64, subprocess

SSH = ["C:/Program Files/Git/usr/bin/ssh.exe", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
       "-o", "ServerAliveInterval=15", "albus@192.168.50.166"]

targets = [
    "/models/unsloth/Qwen3.8-Flash-Next-UD-IQ4_XS/",
    "/models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/",
    "/models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/unsloth-UD-IQ4_XS/",
    "/home/albus/strata166/data/mtp/",
    "/home/albus/strata166/data/mtp/rt/",
]
lines = ["echo '@@ /models 顶层相关项'; ls -l /models | grep -E 'unsloth|huihui-ai'",
         "echo; echo '@@ /home/albus/strata166/weights (本体)'; ls -ld /home/albus/strata166/weights"]
for t in targets:
    lines.append("echo; echo '@@ %s'; ls -l '%s'" % (t, t))
lines.append("echo; echo '@@ 软链解析'")
for f in ["/home/albus/strata166/weights",
          "/models/unsloth/Qwen3.8-Flash-Next-UD-IQ4_XS/mmproj-Qwen3.8-Flash-Next-BF16.gguf",
          "/models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/mtp",
          "/models/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-GGUF/unsloth-UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf",
          "/home/albus/strata166/weights/Qwen3.8-Flash-Next-UD-IQ4_XS-00002-of-00003.gguf"]:
    lines.append("if [ -L '%s' ]; then echo \"LINK | %s | $(readlink '%s') | $( [ -e \"$(readlink -f '%s')\" ] && echo OK || echo BROKEN )\"; "
                 "else echo \"FILE | %s | - | OK\"; fi" % (f, f, f, f, f))
SC = "set -u\n" + "\n".join(lines) + "\n"

p = subprocess.run(SSH + ["base64 -d | bash"], input=base64.b64encode(SC.encode()) + b"\n",
                   capture_output=True, timeout=300)
out = p.stdout.decode("utf-8", "replace")
open(r"D:/workbuddy_space/strata_ws/deploy/tmp/_w714_filelist.txt", "w", encoding="utf-8", newline="\n").write(out)
print(out)
if p.stderr.strip():
    print("ERR:", p.stderr.decode("utf-8", "replace")[-300:])
