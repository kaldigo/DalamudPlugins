# Kaldigo's Dalamud Plugins

One custom repository for Kaldigo's FFXIV/Dalamud plugins.

## Install

In `/xlsettings` â†’ **Experimental** â†’ **Custom Plugin Repositories**, add:

```text
https://raw.githubusercontent.com/kaldigo/DalamudPlugins/main/pluginmaster.json
```

Then open `/xlplugins` and install the plugins you want. If you already use the
HotbarTools repository URL, replace that entry with this URL. Your installed
plugins retain their identities and configuration; reinstalling is unnecessary.

## Plugins

| Plugin | Purpose | Source |
| --- | --- | --- |
| Aetherworks | Individually configurable quality-of-life tools | [HotbarTools](https://github.com/kaldigo/HotbarTools/tree/main/Aetherworks) |
| Accord | Intent settings and matching hotbar layouts | [Accord](https://github.com/kaldigo/Accord) |
| Wrath Combo | Accord-compatible rotation engine fork | [Accord](https://github.com/kaldigo/Accord) |
| ExpandedHotbars Plus | Additional hotbars, with optional close after click or keybind use | [ExpandedHotbars](https://github.com/kaldigo/ExpandedHotbars) |

ExpandedHotbars Plus is based on [MidoriKami's plugin](https://github.com/MidoriKami/ExpandedHotbars).
Search for **ExpandedHotbars Plus** in the installer. Its separate identity
`ExpandedHotbarsPlus` allows installation alongside the official listing. Disable
the upstream plugin before enabling Plus because their commands and hotbars overlap.
Settings are separate; use hotbar export/import to transfer layouts. The original
settings are preserved. Its new auto-close behavior still needs
in-game acceptance testing. Wrath Combo likewise replaces the upstream Wrath Combo;
see its source repository for installation and migration details.

Hotbar Bridge and Job Setup are retired and are not included in this feed.

## Releases and maintenance

This repository is the central installation feed. Plugin source, licenses, build
history, and release downloads remain in the source repositories linked above.
Existing release URLs remain valid.

The feed refreshes hourly from the maintained source feeds in `sources.json`, or
on demand through **Actions â†’ Refresh plugin feed â†’ Run workflow**. GitHub may
delay scheduled runs or disable schedules in inactive repositories. Each update
validates every source before replacing the feed; a failed refresh preserves the
last published feed. Development previews may be included, as described by each
plugin's release notes.

ExpandedHotbars separately checks upstream daily. Routine condition/documentation
updates merge after build, configuration, policy and packaging checks pass. Changes
to fork-modified files, dependencies, publishing or unrecognised areas remain open
for manual review, as do conflicts and failed checks. Each routine automatic merge
queues a fresh versioned preview release after rebuilding the exact merged source
and passing every regression check. The source feed updates only after release
assets are public and their checksums pass. The central feed then refreshes hourly;
Dalamud can install the newer version through its normal plugin update process.

Release retries reuse the same source/version, resume incomplete drafts, and recover
missed feed updates. Published assets are not overwritten and feeds cannot move
backwards to an older version. GitHub delays or failed checks can delay publication;
the last working release remains available.

## Adding plugins

New plugins must declare a release policy in `release-policies.json`. The shared
version planner and validated publisher live in `.github/actions/plan-release` and
`.github/actions/publish-release`. See [the onboarding standard](docs/ADDING-PLUGINS.md)
for the source workflow contract, checks and manual-review boundaries. Aetherworks,
Accord and Wrath Combo retain their existing source-managed release workflows.

To validate this repository locally:

```text
python tools/sync_feed.py --check
```

To refresh from the source feeds:

```text
python tools/sync_feed.py
```

This is an independent custom repository, not affiliated with Dalamud or the
upstream plugin authors. Original licenses and attribution remain with each source.
