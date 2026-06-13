pause
REM @echo off
cd /d "%~dp0"
echo ===================================================
echo   MEMULAI PROSES KOMPILASI WINDOWS INSTALLER EXE
echo ===================================================
echo.

REM 1. Jalankan PyInstaller untuk membuat PackFlow.exe
echo >>> Membangun file executable (EXE)...
pause
python build_exe.py
pause
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Gagal membangun file EXE!
    pause
    exit /b %ERRORLEVEL%
)

REM 2. Pastikan folder output dibersihkan
if exist installer_dist rmdir /s /q installer_dist

REM 3. Jalankan Inno Setup Compiler (ISCC)
echo >>> Mengompilasi installer.iss...
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Kompilasi Gagal! Silakan periksa log di atas.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ===================================================
echo   SUKSES! Installer dibuat di:
echo   d:\PackFlow Apps\PackFlow - v2.0\installer_dist\PackFlow_Setup.exe
echo ===================================================
echo.
pause
