import sys
sys.path.insert(0, "/src/projects/hipblaslt/tensilelite")
from Tensile import LibraryIO

P = ("/g/gen16/1_BenchmarkProblems/"
     "Cijk_Ailk_Bjlk_HHS_BH_UserArgs_00/00_Final/caches/d95bdc892bfc/source/library/gfx906/TensileLibrary.yaml")
d = LibraryIO.read(P, "yaml")
print("top keys:", list(d))
for i, row in enumerate(d.get("library", {}).get("rows", [])):
    print(" row", i, "keys:", list(row))
s = d["solutions"][0]
print("solution keys:", list(s))
print("hardwarePredicate in solution:", "hardwarePredicate" in s)
print("hardwarePredicate in rows:", any("hardwarePredicate" in r for r in d.get("library", {}).get("rows", [])))
