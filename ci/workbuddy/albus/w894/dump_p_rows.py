from pathlib import Path

reg = Path(r"D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv")
want = {"P00","P01","P04","P07","P20","P23","P31","P34","P47","P62","P65","P99","P105","P129","P224"}
out = []
for line in reg.read_text(encoding="utf-8", errors="replace").splitlines():
    f = line.split("\t")
    if f[0] in want:
        out.append(f"===== {f[0]} | {f[2]} | {f[5]} =====\n" + "\n".join(f[2:]) + "\n")
Path(r"D:/workbuddy_space/strata_ws/albus/w894/p_rows.txt").write_text("\n".join(out), encoding="utf-8")
print(f"rows={len(out)} chars={sum(map(len,out))}")
