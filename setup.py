from setuptools import setup

APP = ["claude_usage_monitor.py"]
DATA_FILES = []
OPTIONS = {
    "argv_emulation": False,
    "plist": {
        "LSUIElement": True,  # No Dock icon
        "CFBundleName": "Claude Usage Monitor",
        "CFBundleIdentifier": "com.local.claude-usage-monitor",
    },
    "packages": ["rumps", "requests"],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
