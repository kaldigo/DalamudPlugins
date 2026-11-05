# Built-in Dalamud testing channels

Use the existing repository URL:

```text
https://raw.githubusercontent.com/kaldigo/DalamudPlugins/main/pluginmaster.json
```

- **Accord:** stable releases plus opt-in releases from its `testing` branch.
- **Wrath Combo:** stable releases plus opt-in releases from its `testing` branch.
- **Rotation Solver Reborn:** testing-only releases from `kaldigo/RotationSolverReborn`; no stable RSR channel is offered here. Its `RotationSolver` identity is unchanged.

In `/xlsettings` > **Experimental**, enable **Get plugin testing builds**. In `/xlplugins`, right-click Accord and Wrath Combo and enable **Receive plugin testing versions**, then update. Install Rotation Solver Reborn's testing version from this same repository. Expected versions: Accord **0.2.15.15**, Wrath **1.0.4.38**, RSR **7.5.7.16**.

Existing Accord/Wrath installations from this main repository need neither a new repository nor reinstallation. If RSR was installed from the upstream repository, its source must be switched by reinstalling from this repository while retaining its data. Do not use **Reset plugin data**. If you already followed the superseded separate-testing-repository instructions, reinstall those entries from the main repository while retaining data; simply removing a repository does not change an installed plugin's recorded source. The old testing URL is retained only as a compatibility mirror of main.

## Temporary diagnostics

Open `/accord` > **Rotation testing**, enable **Temporary detailed logging**, and confirm all three components say **recording**. Click **Refresh** in the older capture controls to show the experimental provider options; configure the features to exercise outside combat. Logging does not enable gameplay features, and the old 60-second capture need not be started.

Use **Mark this moment** to describe unexpected behavior or something that failed to trigger. Stop recording, wait for file writing to finish, then **Export diagnostic ZIP**. Nothing is uploaded automatically. The ZIP includes decisions, failed/skipped checks, settings, hotbars, targets, resources, forecasts, queues, confirmations, handoffs and capture-health information.

## Publication and stable independence

The ordinary main-feed refresh reads current stable source feeds, verifies testing ZIPs/checksums and adds the testing fields to the same entries. It refreshes hourly and when registrations change. Stable versions and install/update URLs stay unchanged. If a testing package is unavailable or fails verification, it is omitted rather than blocking a valid stable update. RSR is never substituted with an upstream stable release. A newer stable Accord/Wrath supersedes an older test.

Testing releases remain immutable tagged packages; no plugin source changes or replacement archives were needed for this distribution correction.
