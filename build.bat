@echo off
REM Lokaal een exe bouwen (Windows). Resultaat: dist\PC-LED-Beheer.exe
python -m pip install -r requirements-dev.txt || goto :error
python -m PyInstaller --noconfirm --clean --onefile --windowed --name PC-LED-Beheer pc_led_beheer.py || goto :error
echo.
echo Klaar: dist\PC-LED-Beheer.exe
goto :eof
:error
echo Bouwen mislukt.
exit /b 1
