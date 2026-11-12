<#
.SYNOPSIS
    Builds the official OpenSource Repo Grabber native executable and installs shortcuts.
.DESCRIPTION
    Generates multi-resolution .ico/.png assets, compiles a native Windows GUI launcher
    with embedded icon via csc.exe, and creates shortcuts in C:\ProjectsLauncher,
    the Start Menu, and Desktop.
#>

$ErrorActionPreference = "Stop"

$repoDir = $PSScriptRoot
$assetsDir = Join-Path $repoDir "assets"
$icoPath = Join-Path $assetsDir "icon.ico"
$pngPath = Join-Path $assetsDir "icon.png"
$launcherCs = Join-Path $repoDir "launcher.cs"
$repoExe = Join-Path $repoDir "OpenSourceRepoGrabber.exe"
$projectsLauncherDir = "C:\ProjectsLauncher"

Write-Host "==> Ensuring directories exist..." -ForegroundColor Cyan
if (!(Test-Path $assetsDir)) { New-Item -ItemType Directory -Path $assetsDir -Force | Out-Null }
if (!(Test-Path $projectsLauncherDir)) { New-Item -ItemType Directory -Path $projectsLauncherDir -Force | Out-Null }

Write-Host "==> Compiling native GUI launcher..." -ForegroundColor Cyan
$csc = "C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if (!(Test-Path $csc)) {
    $csc = (Get-Command csc.exe -ErrorAction SilentlyContinue).Source
}

if ($csc -and (Test-Path $csc)) {
    & $csc /target:winexe /win32icon:$icoPath /out:$repoExe /r:System.Windows.Forms.dll,System.dll $launcherCs
    Write-Host "Compiled: $repoExe" -ForegroundColor Green
    
    $launcherExe = Join-Path $projectsLauncherDir "OpenSourceRepoGrabber.exe"
    Copy-Item $repoExe -Destination $launcherExe -Force
    Write-Host "Copied to: $launcherExe" -ForegroundColor Green
} else {
    Write-Warning "csc.exe not found. Skipping C# compilation."
}

Write-Host "==> Creating Windows Shell Shortcuts (.lnk)..." -ForegroundColor Cyan
$wsh = New-Object -ComObject WScript.Shell
$targetExe = Join-Path $projectsLauncherDir "OpenSourceRepoGrabber.exe"
if (!(Test-Path $targetExe)) { $targetExe = $repoExe }

# 1. In C:\ProjectsLauncher
$plLnk = Join-Path $projectsLauncherDir "OpenSource Repo Grabber.lnk"
$s1 = $wsh.CreateShortcut($plLnk)
$s1.TargetPath = $targetExe
$s1.WorkingDirectory = $repoDir
$s1.IconLocation = "$icoPath,0"
$s1.Description = "OpenSource Repo Grabber - The definitive desktop exploration and contribution hub for open-source software"
$s1.Save()
Write-Host "Created: $plLnk" -ForegroundColor Green

# 2. In Start Menu Programs
$startMenuDir = [System.IO.Path]::Combine($env:APPDATA, "Microsoft\Windows\Start Menu\Programs")
$startLnk = Join-Path $startMenuDir "OpenSource Repo Grabber.lnk"
$s2 = $wsh.CreateShortcut($startLnk)
$s2.TargetPath = $targetExe
$s2.WorkingDirectory = $repoDir
$s2.IconLocation = "$icoPath,0"
$s2.Description = "OpenSource Repo Grabber - The definitive desktop exploration and contribution hub for open-source software"
$s2.Save()
Write-Host "Created: $startLnk" -ForegroundColor Green

# 3. On Desktop
$desktopDir = [System.Environment]::GetFolderPath("Desktop")
$deskLnk = Join-Path $desktopDir "OpenSource Repo Grabber.lnk"
$s3 = $wsh.CreateShortcut($deskLnk)
$s3.TargetPath = $targetExe
$s3.WorkingDirectory = $repoDir
$s3.IconLocation = "$icoPath,0"
$s3.Description = "OpenSource Repo Grabber - The definitive desktop exploration and contribution hub for open-source software"
$s3.Save()
Write-Host "Created: $deskLnk" -ForegroundColor Green

# 4. Batch fallbacks
$batContent = @"
@echo off
title OpenSource Repo Grabber Launcher
cd /d "$repoDir"
start "" "$repoDir\.venv\Scripts\pythonw.exe" run.py %*
"@
Set-Content -Path (Join-Path $projectsLauncherDir "Launch-OpenSourceRepoGrabber.bat") -Value $batContent -Encoding ASCII
Set-Content -Path (Join-Path $repoDir "launch.bat") -Value $batContent -Encoding ASCII

Write-Host "==> Done! Official application launcher is ready in C:\ProjectsLauncher." -ForegroundColor Green
