# Plugin onboarding and release standard

Every new plugin needs a source repository, an immutable release archive, a source
feed, an entry in `sources.json`, and an explicit entry in `release-policies.json`.
An unregistered plugin is rejected by central feed validation. Existing
`source-managed` entries are retained for established plugin release pipelines;
new maintained forks should follow the automatic routine-update contract below.

## Routine updates

Classify the complete upstream change with a conservative allow-list. Any changes
to fork customizations, dependencies, configuration, native activation code,
publishing, automation or unknown areas require manual review. Test the proposed
merge, verify both branch tips, and merge only the exact tested commit. Preserve
upstream ancestry and never force-push the default branch.

After a routine merge, explicitly dispatch the source release workflow with the
source, original base and upstream commit IDs. Bot pushes alone do not start
ordinary push workflows. Re-check eligibility in the release workflow. Keep a
machine-readable receipt on the merged PR and retry missed dispatches on the next
scheduled run. Sensitive/manual merges do not automatically queue releases.

## Shared publishing actions

Use the actions from a reviewed commit of this repository. ExpandedHotbars is the
working implementation to follow, including recovery of failed publication.

1. Check out the exact merged source and initialise pinned submodules.
2. Call `kaldigo/DalamudPlugins/.github/actions/plan-release` with `internal-name`,
   `minimum-version` and `source-commit`. An optional `tag` supports reviewed manual
   releases. Supply the source repository's token through `GH_TOKEN`.
3. Build with the returned four-part `version`, including the actual DLL assembly
   version. This revision is independent of the upstream project's version field.
4. Run plugin-specific regression checks, configuration compatibility checks,
   merge-policy tests and release packaging checks. Native game/UI acceptance
   testing must remain explicit where it cannot run in CI.
5. Package into `artifacts/<InternalName>.zip`, plus `artifacts/pluginmaster.json`
   containing exactly one entry and `artifacts/SHA256SUMS.txt` containing the ZIP
   checksum. The archive must include the matching DLL/manifest, runtime
   dependencies, icons and required license notices. Feed URLs must use the planned
   immutable GitHub release tag and archive name.
6. Call `kaldigo/DalamudPlugins/.github/actions/publish-release` with the source
   `default-branch`. It validates the package, creates/verifies the exact tag,
   uploads to a draft, checks uploaded asset digests, publishes the preview, and
   updates only the source feed. It never force-pushes or replaces published assets.
7. If planning returns `skip=true`, skip the build and packaging but still call
   the publisher: it verifies the existing release and repairs a missed feed update.

Serialise source releases with one concurrency group. Release jobs require only
source `contents: write`; dispatching the workflow requires source `actions: write`.
No cross-repository personal access token is required. The central feed refresh
reads public source feeds and verifies new automatically released archives and
checksums before advertising them. It rejects version downgrades.

The shared publisher currently preserves development-preview distribution.
Promoting a plugin to a stable channel is an explicit reviewed publishing change.
Enabling automatic publication for a new plugin also requires a reviewed source
workflow; adding a feed entry by itself does not authorise arbitrary source builds.
