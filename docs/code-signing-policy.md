# Code signing policy

Free code signing provided by [SignPath.io](https://signpath.io), certificate by [SignPath Foundation](https://signpath.org).

> Status: the application to the SignPath Foundation open-source program is in preparation. Until it is approved, the Windows setup is published **unsigned**.

## What is signed

Only the Windows release artifacts of this project:

- `UPA-Analyzer-Control-<version>-Setup.exe` (installer)
- `UPA-Analyzer-Control.exe` (program inside the installer)

They are built exclusively by GitHub Actions ([`.github/workflows/windows-installer.yml`](../.github/workflows/windows-installer.yml)) from the public source code of this repository on GitHub-hosted runners. Every build is tested automatically (start, user interface, version, icon, chart and test-report generation, exit) before a release is created. Each signing request is approved manually by an approver.

Bundled third-party open-source components (Python runtime and libraries, see [THIRD-PARTY-NOTICES.md](../THIRD-PARTY-NOTICES.md)) are distributed unmodified inside the installer.

## Team roles

| Role | Members |
|---|---|
| Authors (committers) | [techniker67](https://github.com/techniker67) |
| Reviewers | [techniker67](https://github.com/techniker67) |
| Approvers (signing requests) | [techniker67](https://github.com/techniker67) |

All team members use multi-factor authentication for GitHub and SignPath.

## Privacy

This program will not transfer any information to other networked systems unless specifically requested by the user or the person installing or operating it.

- It communicates only with locally connected instruments via serial ports (GPIB adapter, optionally a Fluke multimeter via its IR-USB cable) and with its own user interface via `127.0.0.1`.
- Measurement data is written to the local data folder or to a storage folder chosen by the user (which may be a network share).
- The option `--listen 0.0.0.0` makes the user interface reachable from the local network; it is off by default and only used when the user starts the program with it.
- The program window uses Microsoft Edge WebView2, a component of Windows; its handling of diagnostic data follows the [Microsoft Privacy Statement](https://privacy.microsoft.com/privacystatement) and the user's Windows settings.

## Installation and removal

The setup installs for the current user without administrator rights and can be removed via *Settings → Apps* or the Start-menu entry “UPA-Analyzer-Control deinstallieren”. User data in `Documents\UPA-Analyzer-Control` is kept on uninstall and can be deleted manually. The program makes no other changes to the system configuration.
