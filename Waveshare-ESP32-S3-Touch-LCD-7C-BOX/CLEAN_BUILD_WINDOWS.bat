@echo off
setlocal
echo.
echo WS5000 Waveshare V7.4 clean build
echo ================================
echo.
if exist .pio (
  echo Removing cached PlatformIO dependencies...
  rmdir /s /q .pio
)
pio run
if errorlevel 1 exit /b 1
echo.
echo BUILD SUCCESSFUL
echo Arduino_GFX should report version 1.6.0 in the PlatformIO build log.
endlocal
