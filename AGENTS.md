# Repository maintenance

This is the central plugin install feed and the shared release infrastructure.
Follow `docs/ADDING-PLUGINS.md` when adding any plugin. Do not add a feed entry alone:
register its source and explicit release policy, and equip new maintained forks
with the checked routine-merge and release workflow. Existing source-managed
plugins are listed in `release-policies.json`; do not silently extend that exception
to a new plugin without an explicit owner decision.

Routine automation must preserve fork customizations and pinned dependencies.
Unknown, sensitive, conflicting or failed changes stay manual. Build and test the
exact merged commit, give its actual DLL a newer version, and publish the source
feed only after all immutable release assets and checksums are verified.
Keep retries idempotent, repair missed feed updates, and reject downgrades.

Reuse the shared release actions from a reviewed commit. Changes to release
infrastructure are publishing changes and require review in consuming forks.
Never force-push source branches or replace already-published assets to fix a
release. Recover a draft or issue a newer version instead.

Before publishing repository changes, run:

```text
python -m unittest discover -s tests -p 'test_*.py' -v
python tools/sync_feed.py --check
```
