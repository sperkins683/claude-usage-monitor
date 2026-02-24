#!/usr/bin/env python3
"""Claude Usage Monitor - macOS menu bar app for Claude Pro/Max subscription usage."""

import json
import subprocess
import threading
from datetime import datetime, timezone

import requests
import rumps

API_URL = "https://api.anthropic.com/api/oauth/usage"
POLL_INTERVAL = 120  # seconds
KEYCHAIN_SERVICE = "Claude Code-credentials"


def get_oauth_token():
    """Read OAuth token from macOS Keychain via the security CLI."""
    result = subprocess.run(
        [
            "security",
            "find-generic-password",
            "-s",
            KEYCHAIN_SERVICE,
            "-w",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Keychain lookup failed: {result.stderr.strip()}")
    creds = json.loads(result.stdout.strip())
    # Token is nested: {"claudeAiOauth": {"accessToken": "...", ...}}
    oauth = creds.get("claudeAiOauth", {})
    token = oauth.get("accessToken") or creds.get("accessToken")
    if not token:
        raise RuntimeError("No accessToken found in Keychain credentials")
    return token


def fetch_usage(token):
    """Call the Anthropic OAuth usage endpoint and return parsed JSON."""
    resp = requests.get(
        API_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "anthropic-beta": "oauth-2025-04-20",
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def format_reset_time(iso_str):
    """Format an ISO 8601 reset timestamp into a human-readable string."""
    if not iso_str:
        return "N/A"
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    delta = dt - now
    total_seconds = delta.total_seconds()

    if total_seconds <= 0:
        return "now"

    # Less than 24 hours: show time like "2:30 PM"
    if total_seconds < 86400:
        local_dt = dt.astimezone()
        return local_dt.strftime("%-I:%M %p")

    # Otherwise show day like "Tue Feb 25"
    local_dt = dt.astimezone()
    return local_dt.strftime("%a %b %-d")


def utilization_color(pct):
    """Return a color string for the given utilization percentage."""
    if pct > 80:
        return "red"
    if pct >= 50:
        return "yellow"
    return "green"


def safe_get(obj, key, default=0):
    """Safely get a value from a dict that might be None."""
    if obj is None:
        return default
    return obj.get(key, default)


class ClaudeUsageMonitor(rumps.App):
    def __init__(self):
        super().__init__("Claude Usage", quit_button=None)
        self.title = "5h: ?% | 7d: ?%"
        self.token = None
        self.last_error = None

        # Build the menu structure
        self.menu_5h_header = rumps.MenuItem("── 5-Hour Window ──────────")
        self.menu_5h_usage = rumps.MenuItem("   Usage: —")
        self.menu_5h_reset = rumps.MenuItem("   Resets: —")

        self.menu_7d_header = rumps.MenuItem("── 7-Day Window ───────────")
        self.menu_7d_total = rumps.MenuItem("   Total: —")
        self.menu_7d_opus = rumps.MenuItem("   Opus: —")
        self.menu_7d_sonnet = rumps.MenuItem("   Sonnet: —")
        self.menu_7d_reset = rumps.MenuItem("   Resets: —")

        self.menu_refresh = rumps.MenuItem("Refresh Now", callback=self.on_refresh)
        self.menu_polling = rumps.MenuItem(f"Polling: every {POLL_INTERVAL // 60} min")
        self.menu_error = rumps.MenuItem("")
        self.menu_quit = rumps.MenuItem("Quit", callback=self.on_quit)

        self.menu = [
            self.menu_5h_header,
            self.menu_5h_usage,
            self.menu_5h_reset,
            None,  # separator
            self.menu_7d_header,
            self.menu_7d_total,
            self.menu_7d_opus,
            self.menu_7d_sonnet,
            self.menu_7d_reset,
            None,  # separator
            self.menu_refresh,
            self.menu_polling,
            self.menu_error,
            None,  # separator
            self.menu_quit,
        ]

        # Hide error item initially
        self.menu_error.title = ""

        # Set up polling timer
        self.timer = rumps.Timer(self.poll, POLL_INTERVAL)
        self.timer.start()

        # Immediate first fetch in background
        threading.Thread(target=self.poll, args=(None,), daemon=True).start()

    def poll(self, timer):
        """Timer callback: fetch usage and update display."""
        try:
            if self.token is None:
                self.token = get_oauth_token()
            data = fetch_usage(self.token)
            self.last_error = None
            self.update_display(data)
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 401:
                # Token may have expired, try refreshing it
                self.token = None
                try:
                    self.token = get_oauth_token()
                    data = fetch_usage(self.token)
                    self.last_error = None
                    self.update_display(data)
                    return
                except Exception as retry_err:
                    self.last_error = str(retry_err)
            else:
                self.last_error = str(e)
            self.show_error()
        except Exception as e:
            self.last_error = str(e)
            self.show_error()

    def update_display(self, data):
        """Update the menu bar title and dropdown items with fresh data."""
        five_hour = data.get("five_hour")
        seven_day = data.get("seven_day")
        seven_day_opus = data.get("seven_day_opus")
        seven_day_sonnet = data.get("seven_day_sonnet")

        pct_5h = safe_get(five_hour, "utilization", 0)
        pct_7d = safe_get(seven_day, "utilization", 0)
        pct_opus = safe_get(seven_day_opus, "utilization", 0)
        pct_sonnet = safe_get(seven_day_sonnet, "utilization", 0)

        # Menu bar title
        max_pct = max(pct_5h, pct_7d)
        color = utilization_color(max_pct)

        self.title = f"5h: {pct_5h:.0f}% | 7d: {pct_7d:.0f}%"

        # Update dropdown items
        self.menu_5h_usage.title = f"   Usage: {pct_5h:.1f}%"
        self.menu_5h_reset.title = f"   Resets: {format_reset_time(safe_get(five_hour, 'resets_at', None))}"

        self.menu_7d_total.title = f"   Total: {pct_7d:.1f}%"
        self.menu_7d_opus.title = f"   Opus: {pct_opus:.1f}%"
        self.menu_7d_sonnet.title = f"   Sonnet: {pct_sonnet:.1f}%"
        self.menu_7d_reset.title = f"   Resets: {format_reset_time(safe_get(seven_day, 'resets_at', None))}"

        # Clear any previous error
        self.menu_error.title = ""

        # Update title color via NSAttributedString
        self._set_title_color(color)

    def _set_title_color(self, color):
        """Set the menu bar title color using NSAttributedString via PyObjC."""
        try:
            from AppKit import (
                NSAttributedString,
                NSColor,
                NSFont,
                NSFontAttributeName,
                NSForegroundColorAttributeName,
            )

            color_map = {
                "green": NSColor.systemGreenColor(),
                "yellow": NSColor.systemYellowColor(),
                "red": NSColor.systemRedColor(),
            }

            ns_color = color_map.get(color, NSColor.labelColor())
            font = NSFont.monospacedSystemFontOfSize_weight_(12, 0.0)

            attrs = {
                NSForegroundColorAttributeName: ns_color,
                NSFontAttributeName: font,
            }
            attributed_title = NSAttributedString.alloc().initWithString_attributes_(
                self.title, attrs
            )

            # rumps stores the status item on the App instance
            status_item = self._nsapp.nsstatusitem
            if status_item:
                button = status_item.button()
                if button:
                    button.setAttributedTitle_(attributed_title)
        except ImportError:
            pass
        except Exception:
            pass

    def show_error(self):
        """Show error state in menu bar and dropdown."""
        self.title = "5h: ?% | 7d: ?%"
        if self.last_error:
            err_display = self.last_error[:80]
            self.menu_error.title = f"   Error: {err_display}"
        else:
            self.menu_error.title = "   Error: unknown"

    def on_refresh(self, sender):
        """Handle 'Refresh Now' click."""
        self.title = "5h: …"
        threading.Thread(target=self.poll, args=(None,), daemon=True).start()

    def on_quit(self, sender):
        """Handle 'Quit' click."""
        rumps.quit_application()


if __name__ == "__main__":
    ClaudeUsageMonitor().run()
