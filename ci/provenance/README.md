# Provenance

- `workspace_manifest.tsv` - SHA-256 of every auditable WorkBuddy workspace file.
- `selected_scripts.tsv` - SHA-256 of every script/patch copied into `ci/workbuddy`.
- `HISTORY_CORRECTIONS.md` - corrections to W1045/W1046 CI claims and current limits.

Regenerate from the WorkBuddy workspace with `albus/w1047/build_bundle.py`.
The GitHub workflow cannot see the laptop workspace, so the checked-in manifest
is the bridge between local artifacts and CI-visible provenance.
