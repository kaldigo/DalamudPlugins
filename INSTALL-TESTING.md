# Accord / Wrath / RSR testing installation

Custom repository URL (copy the complete line):

```text
https://raw.githubusercontent.com/kaldigo/DalamudPlugins/testing/testing-pluginmaster.json
```

1. Open `/xlsettings`, select **Experimental**, add the URL under **Custom Plugin Repositories**, enable it, and enable **Get plugin testing builds**. Save.
2. Open `/xlplugins`. Choose the entries supplied by the testing repository. Enable **Receive plugin testing versions** in each plugin's context menu, or choose **Install testing version**.
3. Confirm the versions: Accord **0.2.15.15**, Wrath Combo **1.0.4.38**, Rotation Solver **7.5.7.16**.

For plugins already installed from another repository, adding this URL alone does not switch their update source. Dalamud associates updates with the installation repository. Uninstall the old plugin entry and reinstall its testing entry from this URL; retain the existing plugin data (do not use **Reset plugin data**). The plugin identities and settings directories are unchanged. Keep other repositories for their other plugins. Install only one copy of each plugin; dev-plugin copies must not run alongside installed copies.

This is plugin testing, not a request to change Dalamud itself to staging. See the [official testing instructions](https://goatcorp.github.io/faq/dalamud_troubleshooting.html#q-how-do-i-enable-plugin-test-builds) and [Dalamud's source-repository update matching](https://github.com/goatcorp/Dalamud/blob/master/Dalamud/Plugin/Internal/PluginManager.cs).

## Logging while playing

- Open `/accord` and select **Rotation testing**.
- Enable **Temporary detailed logging** and verify that all three components show **recording**.
- Click **Refresh** in the existing capture controls to load the experimental provider settings, then enable the job/targeting options and automation you want to exercise outside combat. Logging does not enable or change them. The older 60-second capture does not need to be started.
- When an expected action does not happen, enter a note and press **Mark this moment**.
- Stop logging, wait for the components to finish writing, then select **Export diagnostic ZIP**. Give the resulting ZIP or its local path to the assistant for review.

Logs include selections and rejections, feature evaluation, actual hotbar slots, settings, targets, job gauges, cooldowns, forecasts, action queue/send/confirmation data and automation handoffs. Missing components, loss counters and file errors are visible. The session survives job and territory changes, is off after reload, and stops if the controller is lost. Nothing is uploaded automatically.

[Detailed diagnostic coverage and analysis](https://github.com/kaldigo/FFXIVAccord/blob/testing/docs/rotation-redesign/session-diagnostics.md).

## Stable updates and returning to stable

The testing feed refreshes current stable entries hourly and overlays only the three verified testing candidates. Stable versions and download links remain the upstream values. A newer stable release can supersede an older test. Regular stable development and publication remain independent.

To leave testing, disable **Receive plugin testing versions** for these plugins and reinstall their stable version if necessary; retain plugin data. Experimental provider toggles and diagnostic logging are session-only. Reinstalling from your original repository also restores that update source. These releases use the same identities, so they replace the installed version rather than creating a parallel installation.
