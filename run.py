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

# Import and run the GUI
from gui import main

if __name__ == "__main__":
    print("=" * 50)
    print("  OpenSource Repo Grabber")
    print("=" * 50)
    print()
    print("Starting application...")
    print()
    
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        input("Press Enter to exit...")
