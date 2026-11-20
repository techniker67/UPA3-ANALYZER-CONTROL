@echo off
cd /d "%~dp0"
title UPA-Software (Fenster offen lassen)
where python >nul 2>nul
if %errorlevel%==0 (python upa_server.py %*) else (py -3 upa_server.py %*)
pause
