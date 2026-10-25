# Kaldigo's Dalamud Plugins

One custom repository for Kaldigo's FFXIV/Dalamud plugins.

## Install

In `/xlsettings` → **Experimental** → **Custom Plugin Repositories**, add:

```text
https://raw.githubusercontent.com/kaldigo/DalamudPlugins/main/pluginmaster.json
```

Then open `/xlplugins` and install the plugins you want. If you already use the
HotbarTools repository URL, replace that entry with this URL. Your installed
plugins retain their identities and configuration; reinstalling is unnecessary.

## Plugins

| Plugin | Purpose | Source |
| --- | --- | --- |
| Aetherworks | Individually configurable quality-of-life tools | [FFXIVAetherworks](https://github.com/kaldigo/FFXIVAetherworks) |
| Accord | Intent settings and matching hotbar layouts | [FFXIVAccord](https://github.com/kaldigo/FFXIVAccord) |
| Wrath Combo | Accord-compatible rotation engine fork | [WrathCombo](https://github.com/kaldigo/WrathCombo) |
| ExpandedHotbars Plus | Additional hotbars, with optional close after click or keybind use | [ExpandedHotbars](https://github.com/kaldigo/ExpandedHotbars) |
| AutoRetainer | Original identity and workflows, with optional Steward item-policy integration | [AutoRetainer](https://github.com/kaldigo/AutoRetainer) |
| Steward | Collection protection, exclusions, sale rules and inventory decisions for the AutoRetainer fork | [FFXIVSteward](https://github.com/kaldigo/FFXIVSteward) |

ExpandedHotbars Plus is based on [MidoriKami's plugin](https://github.com/MidoriKami/ExpandedHotbars).
Search for **ExpandedHotbars Plus** in the installer. It uses the separate identity
`ExpandedHotbarsPlus`, allowing installation alongside the official listing.
Disable the upstream ExpandedHotbars before enabling Plus because their commands
and hotbars overlap. Settings are separate; use hotbar export/import to transfer
layouts. The original settings are preserved. Its new auto-close behavior still needs
in-game acceptance testing. Wrath Combo likewise replaces the upstream Wrath Combo;
see its source repository for installation and migration details.

Hotbar Bridge and Job Setup are retired and are not included in this feed.

AutoRetainer replaces the upstream installation using the same `AutoRetainer` identity, commands and configuration, with a recoloured original icon. Steward is a separate companion and starts in dry run. Both Metallic Silver dye items are initially excluded. Open `/steward` for decisions and settings. These are development previews; native game acceptance is pending. Never enable two AutoRetainer copies together. The fork checks upstream daily and tests proposed merges; routine unrelated method-body/documentation changes can merge and release automatically once GitHub's update-PR creation permission is enabled. Conflicts, protected code, dependencies, configuration and publishing changes remain review work.

## Releases and maintenance

This repository is the central installation feed. Plugin source, licenses, build
history, and release downloads remain in the source repositories linked above.
HotbarTools is retired. The former Accord repository is now WrathCombo, preserving its upstream fork relationship and history.

The feed refreshes hourly from the maintained source feeds in `sources.json`, or
on demand through **Actions → Refresh plugin feed → Run workflow**. GitHub may
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
for the source workflow contract, checks and manual-review boundaries.
Accord and Aetherworks use reviewed source workflows that publish updates on main automatically. Wrath Combo also publishes reviewed main updates and checks upstream daily, automatically merging only untouched documentation changes. All three use the shared planner and checksum-verified publisher.

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
