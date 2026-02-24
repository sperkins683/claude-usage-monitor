# Claude Usage Monitor

A macOS menu bar app that displays your Claude Pro/Max subscription usage at a glance.

![menu bar](https://img.shields.io/badge/macOS-menu%20bar-blue)
![python](https://img.shields.io/badge/python-3.9+-green)

## What it does

Shows your Claude usage directly in the macOS menu bar:

```
5h: 56% | 7d: 14%
```

Click to see a detailed breakdown:

```
── 5-Hour Window ──────────
   Usage: 56.0%
   Resets: 9:00 PM
── 7-Day Window ───────────
   Total: 14.0%
   Opus: 0.0%
   Sonnet: 0.0%
   Resets: Thu Feb 26
───────────────────────────
   Refresh Now
   Polling: every 2 min
───────────────────────────
   Quit
```

The title is color-coded based on the highest utilization:
- **Green**: < 50%
- **Yellow**: 50–80%
- **Red**: > 80%

## Prerequisites

- macOS
- Python 3.9+
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated (stores the OAuth token in Keychain)

## Install

```bash
git clone https://github.com/sperkins683/claude-usage-monitor.git
cd claude-usage-monitor
pip3 install -r requirements.txt
```

### Run directly

```bash
python3 claude_usage_monitor.py
```

### Build a standalone .app

```bash
python3 setup.py py2app
cp -R dist/"Claude Usage Monitor.app" ~/Applications/
```

### Launch at login (optional)

```bash
osascript -e 'tell application "System Events" to make login item at end with properties {path:"'$HOME'/Applications/Claude Usage Monitor.app", hidden:false, name:"Claude Usage Monitor"}'
```

## How it works

1. Reads the OAuth token from the macOS Keychain entry `Claude Code-credentials` (written by Claude Code on login)
2. Polls `GET https://api.anthropic.com/api/oauth/usage` every 2 minutes
3. Displays the 5-hour rolling window and 7-day weekly limit utilization in the menu bar
4. Automatically retries with a fresh token on 401 errors

## Uninstall

```bash
# Remove the app
rm -rf ~/Applications/"Claude Usage Monitor.app"

# Remove from login items
osascript -e 'tell application "System Events" to delete login item "Claude Usage Monitor"'
```
