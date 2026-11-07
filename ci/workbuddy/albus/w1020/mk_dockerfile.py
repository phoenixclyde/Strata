import io

src = "/home/albus/strata166/build-ctx-210/Dockerfile-0.2.10"
dst = "/home/albus/strata166/build-ctx-211/Dockerfile-0.2.11"
s = io.open(src, encoding="utf-8").read()

s = s.replace("v0.2.10, engine 0.1.56", "v0.2.11, engine 0.1.56")
s = s.replace("与 0.2.9-101 的差异：/src 换成 rebase 到 upstream v0.2.10 的树（37 条 gfx906 提交重放）；",
              "与 0.2.10-101 的差异：/src 换成 rebase 到 upstream v0.2.11（9f7d977d）的树（64 条提交重放，线性）；")
s = s.replace("strata-src-0.2.10.tar.gz", "strata-src-0.2.11.tar.gz")

old_json = ('echo "{\\"source\\": \\"rebase onto upstream v0.2.10 (ffa80d73) from gfx906/mi50 d963c791\\", '
            '\\"commits_on_top\\": 37, \\"engine\\": \\"0.1.56\\", \\"rebase_date\\": \\"2026-11-04\\"}" > /src/BUILD-IMAGE.json')
new_json = ('echo "{\\"source\\": \\"rebase onto upstream v0.2.11 (9f7d977d) from gfx906/mi50\\", '
            '\\"commits_on_top\\": 64, \\"engine\\": \\"0.1.56\\", \\"rebase_date\\": \\"2026-11-06\\", '
            '\\"llama_cpp\\": \\"3cf0325\\"}" > /src/BUILD-IMAGE.json')
assert old_json in s, "json line not found"
s = s.replace(old_json, new_json)

io.open(dst, "w", encoding="utf-8", newline="\n").write(s)
print("written", len(s))
