@echo off
REM Double-click or run from cmd: scripts\launch.bat
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch.ps1" %*
