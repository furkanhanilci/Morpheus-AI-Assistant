@echo off
REM ============================================================
REM  MARK XXXIX — Windows launcher
REM  Cift tikla -> ilk kurulum varsa yapar, sonra calistirir
REM ============================================================
setlocal enabledelayedexpansion

cd /d "%~dp0"

REM ----- Python tespiti — 3.12'yi tercih et, sonra py launcher, sonra system -----
set "PYEXE="

REM 1) py launcher ile spesifik surum dene (en guvenli)
where py >nul 2>nul
if not errorlevel 1 (
    for %%V in (3.12 3.11) do (
        py -%%V -c "import sys" >nul 2>nul
        if not errorlevel 1 (
            for /f "delims=" %%P in ('py -%%V -c "import sys; print(sys.executable)"') do (
                set "PYEXE=%%P"
                goto :found
            )
        )
    )
)

REM 2) PATH'teki python'a bak
where python >nul 2>nul
if not errorlevel 1 (
    for /f "delims=" %%P in ('python -c "import sys; print(sys.executable)"') do (
        set "PYEXE=%%P"
    )
)

:found
if "!PYEXE!" == "" (
    echo.
    echo [HATA] Python bulunamadi.
    echo.
    echo Python 3.11 veya 3.12 kurun:
    echo https://www.python.org/downloads/release/python-3128/
    echo.
    echo Kurulumda "Add Python to PATH" secenegini isaretlemeyi unutmayin.
    echo.
    pause
    exit /b 1
)

REM ----- Python surum kontrolu — 3.13+ uyari -----
"!PYEXE!" -c "import sys; sys.exit(0 if sys.version_info[:2] in [(3,11),(3,12)] else 1)" >nul 2>nul
if errorlevel 1 (
    echo.
    echo [UYARI] Bulunan Python surumu desteklenmiyor olabilir.
    "!PYEXE!" --version
    echo.
    echo Bu proje Python 3.11 veya 3.12 ile test edildi.
    echo sounddevice gibi paketler yeni surumler icin wheel saglamiyor olabilir.
    echo.
    set /p "CHOICE=Devam etmek istiyor musunuz? (E/H): "
    if /i not "!CHOICE!" == "E" (
        echo Iptal edildi.
        pause
        exit /b 1
    )
)

echo [INFO] Python: !PYEXE!

REM ----- venv yoksa olustur -----
if not exist ".venv\Scripts\python.exe" (
    echo.
    echo [SETUP] Sanal ortam olusturuluyor...
    "!PYEXE!" -m venv .venv
    if errorlevel 1 (
        echo [HATA] Sanal ortam olusturulamadi.
        pause
        exit /b 1
    )
)

REM ----- venv'i aktif et -----
call ".venv\Scripts\activate.bat"

REM ----- Bagimliliklar — flag dosyasi -----
if not exist ".venv\installed.flag" (
    echo.
    echo [SETUP] Bagimliliklar yukleniyor (ilk seferde 2-3 dakika)...
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [HATA] Bagimlilik yuklemesi basarisiz.
        echo Hata mesajini okuyup eksik paketi manuel kurabilirsiniz:
        echo    pip install MODULNAME
        pause
        exit /b 1
    )
    echo. > ".venv\installed.flag"
)

REM ----- Calistir -----
echo.
echo [RUN] MARK XXXIX baslatiliyor...
echo.
python main.py

REM Hata olursa pencere kapanmasin
if errorlevel 1 (
    echo.
    echo Bir hata olustu. Cikis icin bir tusa basin.
    pause
)

endlocal
