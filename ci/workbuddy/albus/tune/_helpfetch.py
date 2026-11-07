import subprocess, base64
HOST = "albus@192.168.50.166"
SH = r'''
docker exec strata166-407 /src/build-906/strata --help 2>&1
'''
b64 = base64.b64encode(SH.encode()).decode("ascii")
p = subprocess.run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=10",HOST,"base64 -d | bash"],
                   input=b64.encode("ascii"), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
out = p.stdout.decode("utf-8","replace")
open(r"D:/workbuddy_space/strata_ws/albus/tune/_help0147.txt","w",encoding="utf-8").write(out)
print("RC",p.returncode,"lines",out.count("\n"),"bytes",len(out))
