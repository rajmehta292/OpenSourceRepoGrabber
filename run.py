#!/usr/bin/env python3
"""
OpenSource Repo Grabber - Launcher Script
"""
import sys
import os

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
