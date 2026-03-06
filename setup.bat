@echo off
echo VM.AI SETUP 

REM check uv
uv --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo uv not found.
    echo Install: https://github.com/astral-sh/uv
    pause
    exit /b
)

echo.
echo Creating venv...
uv venv

echo.
echo Activating...
call .venv\Scripts\activate

echo.
echo Installing dependencies...
uv pip install -r requirements.txt

echo.
echo Creating folders...
mkdir models 2>nul
mkdir data 2>nul

echo.
echo Setup finished.
echo Run training with:
echo     .venv\Scripts\activate
echo     python src/train.py

pause