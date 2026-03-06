@echo off
REM ================================
REM Fast UV Installer for Python Packages
REM Usage: uv-inst.bat package1 package2 ...
REM ================================

REM --- Set cache locations to D: ---
set UV_CACHE_DIR=D:\uv_cache
set HF_HOME=D:\hf_cache
set PIP_CACHE_DIR=D:\pip_cache
set HF_HUB_ENABLE_HF_TRANSFER=1
set UV_LINK_MODE=copy

REM --- Check if packages were provided ---
if "%~1"=="" (
    echo Please provide at least one package name.
    echo Example: uv-inst.bat jupyter matplotlib pandas
    exit /b 1
)

REM --- Build package list ---
set PACKAGES=
:loop
if "%~1"=="" goto done
set PACKAGES=%PACKAGES% %1
shift
goto loop
:done

REM --- Run UV install ---
echo Installing packages: %PACKAGES%
uv pip install %PACKAGES% --no-cache-dir --upgrade

echo ================================
echo Installation completed!
pause