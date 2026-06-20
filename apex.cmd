@echo off
setlocal
set "APEXPOWERS_ROOT=%~dp0"
python "%~dp0src\apexpowers_cli\cli.py" %*
