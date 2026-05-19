@echo off
REM =====================================================================
REM  PROTEIN TRADING - Avvio applicazione Streamlit
REM  Doppio click su questo file per aprire l'app nel browser.
REM
REM  La prima volta crea l'ambiente virtuale e installa le librerie
REM  (puo' richiedere 1-3 minuti). Le volte successive parte in 5 secondi.
REM =====================================================================

setlocal
cd /d "%~dp0"

echo.
echo ========================================
echo   PROTEIN TRADING - Avvio app
echo ========================================
echo.

REM ---------- 1) Verifica che Python sia installato ----------
where py >nul 2>&1
if errorlevel 1 (
    where python >nul 2>&1
    if errorlevel 1 (
        echo [ERRORE] Python non e' installato.
        echo.
        echo Installa Python da: https://www.python.org/downloads/windows/
        echo IMPORTANTE: durante l'installazione spunta "Add Python to PATH".
        echo.
        pause
        exit /b 1
    )
    set PYCMD=python
) else (
    set PYCMD=py
)

REM ---------- 2) Crea venv se non esiste ----------
if not exist "app\.venv\Scripts\python.exe" (
    echo [Setup iniziale] Creo l'ambiente virtuale Python...
    %PYCMD% -m venv "app\.venv"
    if errorlevel 1 (
        echo [ERRORE] Impossibile creare l'ambiente virtuale.
        pause
        exit /b 1
    )
)

REM ---------- 3) Installa requirements se mancanti ----------
REM Controlla TUTTE le librerie principali, non solo streamlit
"app\.venv\Scripts\python.exe" -c "import streamlit, openpyxl, pandas, plotly, reportlab" >nul 2>&1
if errorlevel 1 (
    echo [Setup] Installo / aggiorno le librerie necessarie...
    "app\.venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
    "app\.venv\Scripts\python.exe" -m pip install -r "app\requirements.txt"
    if errorlevel 1 (
        echo [ERRORE] Impossibile installare le librerie.
        pause
        exit /b 1
    )
    echo.
    echo [OK] Setup completato!
    echo.
)

REM ---------- 4) Avvia Streamlit ----------
echo Avvio applicazione...
echo Il browser si aprira' automaticamente su http://localhost:8501
echo.
echo Per chiudere l'app: chiudi questa finestra oppure premi Ctrl+C
echo.

"app\.venv\Scripts\python.exe" -m streamlit run "app\app.py"

pause
