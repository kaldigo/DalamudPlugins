# Opt-in testing composition

This testing branch builds `testing-pluginmaster.json` separately from the stable feed. It reads the live main-branch stable feed every time, plus the explicitly registered upstream RotationSolver stable entry. It never writes `pluginmaster.json` and never freezes stable release versions from this branch.

`testing-sources.json` explicitly registers the three testing repositories. Candidate pointers start empty: no unavailable build is advertised. After source and immutable testing artifacts are published and reviewed, set a pointer to that release's `testing-release.json`. The composer verifies the artifact identity, version, manifest, immutable links and SHA-256 before advertising it. Failed downloads or mismatches leave the previous testing feed intact.

Only the three Dalamud testing fields are overlaid, and only if a candidate is newer than current stable. A newer stable release therefore supersedes an older test without depending on an Accord testing release. Ordinary stable names, versions and install/update links stay as provided by their live sources.

Run `python tools/compose_testing_feed.py --check` for offline registration validation. Registration/composer pushes to testing refresh the testing feed. The prepared `refresh-testing.yml` also supports manual dispatch and hourly refresh, always checking out and writing only the testing branch. GitHub's scheduled/manual workflow availability depends on the workflow being registered on the default branch: promote this one reviewed workflow before advertising a maintained public installation feed. This branch alone does not claim a running schedule.

The shared `publish-testing` action is separate from the stable publisher. It validates the checked-out source against the testing branch and source receipt, verifies the immutable tag and archive, publishes only the candidate JSON/ZIP/checksum/source receipt, and checks all uploaded digests. It can recover draft uploads. Published retries verify byte-identical assets and never replace them or write a source feed. A frozen candidate `pluginmaster.json` is intentionally not published as an install feed. All three consuming forks must pin the reviewed action commit.

Stable Accord is independent. Native installation remains explicit; no plugin is installed by this workflow.
