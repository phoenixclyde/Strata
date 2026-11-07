import io

P = "deploy/W832_OPT_PLAN_V2.md"
s = io.open(P, encoding="utf-8").read()
old = "| 回写 · W1039 §十五（R105：gfx906 的能力缺口一半是构建开关） |"
new = "| 回写 · W1039 §十五（`R105`：gfx906 的能力缺口，一半是构建开关） |"
assert s.count(old) == 1, s.count(old)
io.open(P, "w", encoding="utf-8", newline="\n").write(s.replace(old, new, 1))
print("directory row matched to the heading")
