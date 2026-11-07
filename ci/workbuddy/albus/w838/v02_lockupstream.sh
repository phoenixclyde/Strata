#!/bin/bash
# W838: make pushing to upstream structurally impossible (fetch-only + a pre-push guard)
F=/home/albus/strata166/pr/strata-fork
cd $F || exit 1

echo "=== A. turn the upstream remotes into fetch-only ==="
for r in upstream ghup; do
  git remote set-url --push "$r" "DISABLED-no-push-to-upstream"
  echo "  $r push -> $(git config --get remote.$r.pushurl)"
done

echo
echo "=== B. proof: pushing to upstream now refuses before touching the network ==="
for r in upstream ghup; do
  out=$(git push --dry-run "$r" HEAD:refs/heads/CANARY 2>&1 | head -3)
  echo "  [$r] $out"
done

echo
echo "=== C. install a pre-push guard: only our own fork may receive anything ==="
cat > .git/hooks/pre-push <<'EOF'
#!/bin/sh
# Albus / W838 (2026-10-31): this tree may only push to our own fork.
# Niko1221/Strata is FETCH-ONLY: we track it, we never write to it.
url="$1"
case "$url" in
  *phoenixclyde/Strata*|*phoenixclyde/strata*) exit 0 ;;
  *)
    echo "pre-push: REFUSED. This repo pushes only to phoenixclyde/Strata." >&2
    echo "pre-push: asked for: $url" >&2
    echo "pre-push: upstream is fetch-only by policy (see deploy/W838_REMOTE_POLICY.md)." >&2
    exit 1 ;;
esac
EOF
chmod +x .git/hooks/pre-push
echo "  hook installed: $(ls -l .git/hooks/pre-push | awk '{print $1, $NF}')"

echo
echo "=== D. verify the guard fires on an upstream URL and passes on ours ==="
printf 'refs/heads/x aaa refs/heads/x bbb\n' > /tmp/pp_in
echo "  upstream  -> $(echo 'refs/heads/x aaa refs/heads/x bbb' | .git/hooks/pre-push 'git@github.com:Niko1221/Strata.git' 2>&1; echo "rc=$?")"
echo "  our fork  -> $(echo 'refs/heads/x aaa refs/heads/x bbb' | .git/hooks/pre-push 'git@github.com:phoenixclyde/Strata.git' 2>&1; echo "rc=$?")"

echo
echo "=== E. remotes after ==="
for r in $(git remote); do
  printf "  %-9s fetch=%-62s push=%s\n" "$r" "$(git config --get remote.$r.url)" "$(git config --get remote.$r.pushurl || echo '(same as fetch)')"
done
