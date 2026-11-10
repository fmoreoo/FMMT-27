@echo off
rem Builds the exe and the installer into the dist folder.
rem Needs: python -m pip install pyinstaller. The installer also needs Inno Setup 6.
cd /d "%~dp0reader"
python -m PyInstaller --noconfirm --onefile --windowed --name "FMMT 27" ^
  --icon "%~dp0FMMT 27.ico" ^
  --add-data "%~dp0FMMT 27.html;." ^
  --add-data "%~dp0FMMT 27.ico;." ^
  --distpath "%~dp0dist" --workpath "%TEMP%\fmmt27-build" --specpath "%TEMP%\fmmt27-build" ^
  app.py
if errorlevel 1 (echo Build failed & pause & exit /b 1)
echo.
echo Built the exe in: "%~dp0dist"

set "ISCC="
for %%p in ("%LOCALAPPDATA%\Programs\Inno Setup 6" "%ProgramFiles%\Inno Setup 6" "%ProgramFiles(x86)%\Inno Setup 6") do (
  if exist "%%~p\ISCC.exe" set "ISCC=%%~p\ISCC.exe"
)
if not defined ISCC (
  echo Inno Setup 6 not found, so the installer was skipped.
  exit /b 0
)
"%ISCC%" /Q "%~dp0installer.iss"
if errorlevel 1 (echo Installer build failed & pause & exit /b 1)
echo Built the installer in: "%~dp0dist"
rem checksums to paste into the release notes
powershell -NoProfile -Command "Get-FileHash -Algorithm SHA256 '%~dp0dist\FMMT 27.exe','%~dp0dist\FMMT 27 Setup.exe' | ForEach-Object { $_.Hash.ToLower() + '  ' + (Split-Path $_.Path -Leaf) } | Set-Content -Encoding ascii '%~dp0dist\SHA256SUMS.txt'"
echo Wrote the checksums to: "%~dp0dist\SHA256SUMS.txt"
