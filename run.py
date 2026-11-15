#!/usr/bin/env python3
"""
OpenSource Repo Grabber - Launcher Script
"""
import sys
import os
import ctypes

# Set Windows AppUserModelID so taskbar icon and grouping are distinct
if sys.platform == "win32":
    try:
        app_id = "RajMehta.OpenSourceRepoGrabber.App.1.0"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the GUI (WebView2 + Meta Astryx default; pass --tk for legacy CustomTkinter)
def _launch() -> None:
    if "--tk" in sys.argv:
        from gui import main as tk_main
        tk_main()
        return

    from webview_app import FRONTEND_DIST_DIR, main as webview_main
    if (FRONTEND_DIST_DIR / "index.html").exists():
        webview_main()
    else:
        print("Frontend build not found at frontend/dist — falling back to legacy Tkinter UI.")
        from gui import main as tk_main
        tk_main()


if __name__ == "__main__":
    print("=" * 50)
    print("  OpenSource Repo Grabber")
    print("=" * 50)
    print()
    print("Starting application...")
    print()

    try:
        _launch()
    except Exception as e:
        print(f"Error: {e}")
        if "--no-pause" not in sys.argv and sys.stdin and sys.stdin.isatty():
            input("Press Enter to exit...")
