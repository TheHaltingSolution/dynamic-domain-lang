@echo off
setlocal
set "PROJECT_ROOT=%~1"
if not defined PROJECT_ROOT set "PROJECT_ROOT=C:\Projects\Film_TV_participation_dynamic_DSL"
set "ELAN_HOME=%PROJECT_ROOT%\environment\elan"
if not exist "%ELAN_HOME%\bin\elan.exe" (
  echo Elan not found at "%ELAN_HOME%". See README.md.
  exit /b 1
)
set "PATH=%ELAN_HOME%\bin;%PATH%"
cmd /k
