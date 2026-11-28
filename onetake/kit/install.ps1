# One Take Studio installer for Windows. Right-click this file -> "Run with PowerShell" (or: powershell -ExecutionPolicy Bypass -File install.ps1)
# Installs what's missing (Python, FFmpeg) with winget, sets up One Take's own packages in .venv, makes the built-in
# sounds and offers to install Claude Code. Safe to run again.
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
function Say($t) { Write-Host "`n$t" -ForegroundColor Cyan }
function Refresh-Path { $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User") }

Say "1/5  Checking Python 3.10+"
$py = $null
foreach ($c in @("py -3.12", "py -3.11", "py -3.10", "python")) {
  try { $v = Invoke-Expression "$c -c `"import sys; print(sys.version_info >= (3,10))`"" 2>$null; if ($v -eq "True") { $py = $c; break } } catch {}
}
if (-not $py) {
  winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
  Refresh-Path; $py = "py -3.12"
}
Invoke-Expression "$py --version"

Say "2/5  Checking FFmpeg (video engine)"
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
  winget install -e --id Gyan.FFmpeg --accept-source-agreements --accept-package-agreements
  Refresh-Path
}

Say "3/5  Installing One Take's packages (in this folder only, a few minutes)"
if (-not (Test-Path ".venv")) { Invoke-Expression "$py -m venv .venv" }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip | Out-Null
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt

Say "4/5  Setting up"
foreach ($d in @("drop-in-order", "projects", "library\broll", "library\images", "library\gifs", "library\sounds", "lookbook\looks\custom")) {
  New-Item -ItemType Directory -Force -Path $d | Out-Null
}
& .\.venv\Scripts\python.exe -m engine setup

Say "5/5  Claude Code (the editor)"
if (Get-Command claude -ErrorAction SilentlyContinue) {
  Write-Host "Claude Code is installed."
} else {
  $ans = Read-Host "Claude Code isn't installed. Install it now? (needs a Claude subscription) [Y/n]"
  if ($ans -eq "" -or $ans -match "^[Yy]") { Invoke-RestMethod https://claude.ai/install.ps1 | Invoke-Expression }
  else { Write-Host "Skipped. Install it later from https://claude.com/claude-code" }
}

# a shortcut on the desktop
$ws = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut([Environment]::GetFolderPath("Desktop") + "\One Take Studio.lnk")
$lnk.TargetPath = (Join-Path $PSScriptRoot "Start One Take.bat")
$lnk.WorkingDirectory = $PSScriptRoot
if (Test-Path "assets\icon.ico") { $lnk.IconLocation = (Join-Path $PSScriptRoot "assets\icon.ico") }
$lnk.Save()

Say "All set!"
Write-Host "Start the studio:  double-click 'One Take Studio' on your desktop"
Write-Host "Edit a reel:       put your clips in drop-in-order\, open a terminal in this folder, run  claude"
Write-Host "                   and say: I have a new reel to edit"
Read-Host "Press Enter to close"
