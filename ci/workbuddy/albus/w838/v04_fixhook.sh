#!/bin/bash
# W838: fix the pre-push guard -- $1 is the REMOTE NAME, $2 is the URL
F=/home/albus/strata166/pr/strata-fork
cd $F || exit 1

cat > .git/hooks/pre-push <<'EOF'
#!/bin/sh
# Albus / W838 (2026-10-31): this tree may only push to our own fork.
# Niko1221/Strata is FETCH-ONLY: we track it, we never write to it.
#
# git passes: $1 = remote NAME (e.g. "origin"), $2 = remote URL.
# The URL is what matters: a remote can be renamed.
name="$1"
url="$2"
case "$url" in
  *phoenixclyde/Strata*|*phoenixclyde/strata*) exit 0 ;;
esac
echo "pre-push: REFUSED. This repo pushes only to phoenixclyde/Strata." >&2
echo "pre-push: remote '$name' -> $url" >&2
echo "pre-push: upstream is fetch-only by policy (deploy/W838_REMOTE_POLICY.md)." >&2
exit 1
EOF
chmod +x .git/hooks/pre-push
echo "hook rewritten"
echo
echo "=== A. real push to OUR fork must pass ==="
git push --dry-run origin gfx906/0.2.8-mi50 2>&1 | tail -3
echo "  rc=$?"
echo
echo "=== B. real push to upstream must be refused ==="
git push --dry-run upstream gfx906/0.2.8-mi50 2>&1 | tail -3
echo "  rc=$?"
echo
echo "=== C. real push to ghup must be refused ==="
git push --dry-run ghup gfx906/0.2.8-mi50 2>&1 | tail -2
echo "  rc=$?"
