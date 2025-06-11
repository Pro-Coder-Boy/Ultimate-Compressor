@echo off
:: =================================================================
::  Batch Script to build the Ultimate Image Compressor
:: =================================================================
ECHO.
ECHO  Building the application... Please wait.
ECHO.

:: Clean up previous build directories to ensure a fresh start
IF EXIST build (
    ECHO  - Removing old 'build' directory...
    RMDIR /S /Q build
)
IF EXIST dist (
    ECHO  - Removing old 'dist' directory...
    RMDIR /S /Q dist
)
IF EXIST compressor.spec (
    ECHO  - Removing old '.spec' file...
    DEL compressor.spec
)
ECHO.

:: Run the PyInstaller command to build the application
:: The ^ character allows breaking a long command into multiple lines
python -m PyInstaller ^
    --noconfirm ^
    --windowed ^
    --icon="icon.ico" ^
    --add-data "tools/cjpeg.exe;." ^
    --add-data "tools/cwebp.exe;." ^
    --add-data "tools/pngquant.exe;." ^
    --add-data "tools/zopflipng.exe;." ^
    src/compressor.py

:: Check if the build was successful
IF %ERRORLEVEL% NEQ 0 (
    ECHO.
    ECHO ==========================
    ECHO  !!! BUILD FAILED !!!
    ECHO ==========================
    ECHO An error occurred. Please check the messages above for details.
) ELSE (
    ECHO.
    ECHO =============================================================
    ECHO      Build Succeeded!
    ECHO =============================================================
    ECHO The application is located in the 'dist\compressor' folder.
)

ECHO.
pause
