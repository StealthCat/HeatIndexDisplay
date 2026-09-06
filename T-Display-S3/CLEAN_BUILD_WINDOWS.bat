@echo off
setlocal
echo.
echo WS5000 T-Display-S3 V7.4 clean build
echo ====================================
echo.
if exist .pio (
  echo Removing cached PlatformIO dependencies...
  rmdir /s /q .pio
)
pio run
if errorlevel 1 exit /b 1
echo.
echo BUILD SUCCESSFUL
echo Expected dependency: LovyanGFX @ 1.2.7
echo LilyGo-display-library should NOT appear.
endlocal
