#!/bin/bash
# W838: verify the hook itself with git's real argument order ($1=name, $2=url), avoiding the tail-rc trap
F=/home/albus/strata166/pr/strata-fork
cd $F || exit 1
H=.git/hooks/pre-push

echo "=== A. hook called the way git calls it ==="
printf 'refs/heads/x aaa refs/heads/x bbb\n' > /tmp/ppin

out=$( $H origin "git@github.com:Niko1221/Strata.git" < /tmp/ppin 2>&1 ); rc=$?
echo "  [upstream url ] rc=$rc  ${out%%$'\n'*}"

out=$( $H origin "git@github.com:phoenixclyde/Strata.git" < /tmp/ppin 2>&1 ); rc=$?
echo "  [our fork url ] rc=$rc  ${out:-（安静通过）}"

out=$( $H ghup "https://gh-proxy.com/https://github.com/Niko1221/Strata.git" < /tmp/ppin 2>&1 ); rc=$?
echo "  [ghup url     ] rc=$rc  ${out%%$'\n'*}"

echo
echo "=== B. and the real push paths, with git's own exit code ==="
git push --dry-run origin gfx906/0.2.8-mi50 >/tmp/p1 2>&1; echo "  origin   rc=$?  $(tail -1 /tmp/p1)"
git push --dry-run upstream gfx906/0.2.8-mi50 >/tmp/p2 2>&1; echo "  upstream rc=$?  $(head -1 /tmp/p2)"
git push --dry-run ghup gfx906/0.2.8-mi50 >/tmp/p3 2>&1; echo "  ghup     rc=$?  $(head -1 /tmp/p3)"

echo
echo "=== C. remotes (final) ==="
for r in $(git remote); do
  printf "  %-9s push -> %s\n" "$r" "$(git config --get remote.$r.pushurl || echo '(= fetch url)')"
done
