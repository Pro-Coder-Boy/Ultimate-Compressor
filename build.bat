@echo off
TITLE Ultimate Image Compressor - Build Script
CLS

:: =================================================================
::  Builds both a single-file Portable and a full Installer version.
::  Must be run from the project's root directory.
:: =================================================================

ECHO #############################################################
ECHO #           Building Ultimate Image Compressor            #
ECHO #############################################################
ECHO.

:: --- Define the absolute project root directory ---
SET "ProjectRoot=%~dp0"
IF "%ProjectRoot:~-1%"=="\" SET "ProjectRoot=%ProjectRoot:~0,-1%"

ECHO Project Root Directory is: "%ProjectRoot%"
ECHO.

:: --- 1. Cleanup Phase ---
ECHO [Phase 1/5] Cleaning up previous builds...
IF EXIST "%ProjectRoot%\build" RMDIR /S /Q "%ProjectRoot%\build"
IF EXIST "%ProjectRoot%\dist" RMDIR /S /Q "%ProjectRoot%\dist"
IF EXIST "%ProjectRoot%\compressor.spec" DEL "%ProjectRoot%\compressor.spec" > NUL 2>&1
IF EXIST "%ProjectRoot%\ImageCompressor_Portable.spec" DEL "%ProjectRoot%\ImageCompressor_Portable.spec" > NUL 2>&1
IF EXIST "%ProjectRoot%\InstallerOutput" RMDIR /S /Q "%ProjectRoot%\InstallerOutput"
IF EXIST "%ProjectRoot%\RELEASE" RMDIR /S /Q "%ProjectRoot%\RELEASE"
ECHO    Done.
ECHO.

:: --- 2. Build Portable Version (Single EXE) ---
ECHO [Phase 2/5] Building Portable Version (this may take a moment)...
python -m PyInstaller ^
    --name="ImageCompressor_Portable" ^
    --onefile ^
    --windowed ^
    --icon="%ProjectRoot%\icon.ico" ^
    --add-data "%ProjectRoot%\tools;tools" ^
    --distpath "%ProjectRoot%\dist\portable" ^
    --workpath "%ProjectRoot%\build" ^
    "%ProjectRoot%\src\compressor.py"

IF %ERRORLEVEL% NEQ 0 (
    ECHO. & ECHO !!! PORTABLE BUILD FAILED! Please check the output above. !!!
    pause & exit /b
)
ECHO    Portable build successful.
ECHO.

:: --- 3. Build Folder Version (for Installer) ---
ECHO [Phase 3/5] Building Folder Version for the installer...
IF EXIST "%ProjectRoot%\build" RMDIR /S /Q "%ProjectRoot%\build"
IF EXIST "%ProjectRoot%\compressor.spec" DEL "%ProjectRoot%\compressor.spec" > NUL 2>&1
IF EXIST "%ProjectRoot%\ImageCompressor_Portable.spec" DEL "%ProjectRoot%\ImageCompressor_Portable.spec" > NUL 2>&1

python -m PyInstaller ^
    --name="compressor" ^
    --windowed ^
    --icon="%ProjectRoot%\icon.ico" ^
    --add-data "%ProjectRoot%\tools;tools" ^
    --distpath "%ProjectRoot%\dist" ^
    --workpath "%ProjectRoot%\build" ^
    "%ProjectRoot%\src\compressor.py"

IF %ERRORLEVEL% NEQ 0 (
    ECHO. & ECHO !!! FOLDER BUILD FAILED! Please check the output above. !!!
    pause & exit /b
)
ECHO    Folder build successful.
ECHO.

:: --- 4. Build Installer using Inno Setup ---
ECHO [Phase 4/5] Building Installer (setup.exe)...
SET "ISCC_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
IF NOT EXIST "%ISCC_PATH%" (
    ECHO Inno Setup not found at default location: "%ISCC_PATH%"
    pause
    exit /b
)

IF NOT EXIST "%ProjectRoot%\dist\compressor" (
    ECHO. & ECHO !!! CRITICAL ERROR: The 'dist\compressor' directory was not found! !!!
    pause & exit /b
)

:: Pass the project root directory as a define to the script.
ECHO Compiling Inno Setup script...
"%ISCC_PATH%" /DAppRoot="%ProjectRoot%" "%ProjectRoot%\installer\setup.iss"

IF %ERRORLEVEL% NEQ 0 (
    ECHO. & ECHO !!! INSTALLER BUILD FAILED! Please check Inno Setup output. !!!
    pause & exit /b
)
ECHO    Installer build successful.
ECHO.

:: --- 5. Final Packaging ---
ECHO [Phase 5/5] Packaging final release files...
MKDIR "%ProjectRoot%\RELEASE"
MOVE "%ProjectRoot%\dist\portable\ImageCompressor_Portable.exe" "%ProjectRoot%\RELEASE\"
MOVE "%ProjectRoot%\InstallerOutput\*.exe" "%ProjectRoot%\RELEASE\"
ECHO    Done.
ECHO.

:: Final Cleanup
RMDIR /S /Q "%ProjectRoot%\build"
RMDIR /S /Q "%ProjectRoot%\dist"
RMDIR /S /Q "%ProjectRoot%\InstallerOutput"
IF EXIST "%ProjectRoot%\compressor.spec" DEL "%ProjectRoot%\compressor.spec" > NUL 2>&1
IF EXIST "%ProjectRoot%\ImageCompressor_Portable.spec" DEL "%ProjectRoot%\ImageCompressor_Portable.spec" > NUL 2>&1
ECHO    Cleanup complete.
ECHO.

ECHO =============================================================
ECHO      BUILD PROCESS COMPLETE!
ECHO =============================================================
ECHO Your files are ready in the 'RELEASE' folder.
ECHO.
pause
