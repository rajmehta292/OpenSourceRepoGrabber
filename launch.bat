@echo off
title OpenSource Repo Grabber Launcher
cd /d "C:\Projects\OpenSourceRepoGrabber"
start "" "C:\Projects\OpenSourceRepoGrabber\.venv\Scripts\pythonw.exe" run.py %*
