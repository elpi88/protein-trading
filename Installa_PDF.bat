@echo off
REM =====================================================================
REM  PROTEIN TRADING - Installa reportlab (libreria PDF)
REM
REM  Da usare UNA SOLA VOLTA se l'app dava errore su:
REM  - Fornitori
REM  - Clienti
REM  - Margini
REM
REM  Dopo aver lanciato questo file, chiudi l'app e riavviala con
REM  Avvia_App.bat.
REM =====================================================================

setlocal
cd /d "%~dp0"

echo.
echo ========================================
echo   Installa libreria PDF (reportlab)
echo ========================================
echo.

if not exist "app\.venv\Scripts\python.exe" (
    echo [ERRORE] L'ambiente Python non e' stato ancora creato.
    echo Lancia prima Avvia_App.bat almeno una volta.
    echo.
    pause
    exit /b 1
)

echo Installo reportlab...
echo.

"app\.venv\Scripts\python.exe" -m pip install "reportlab>=4.0"
if errorlevel 1 (
    echo.
    echo [ERRORE] Installazione non riuscita.
    echo Controlla la connessione internet e riprova.
    pause
    exit /b 1
)

echo.
echo ========================================
echo   [OK] reportlab installato!
echo ========================================
echo.
echo Ora puoi chiudere questa finestra e riavviare l'app
echo con Avvia_App.bat.
echo.
pause
