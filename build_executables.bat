@echo off
echo ========================================
echo    MediaUtils EXE Builder
echo ========================================
echo.

REM Prüfe ob PyInstaller installiert ist
python -c "import PyInstaller" 2>nul
if %errorlevel% neq 0 (
    echo ERROR: PyInstaller ist nicht installiert!
    echo Installiere mit: pip install pyinstaller
    pause
    exit /b 1
)

echo ✅ PyInstaller gefunden
echo.

REM Erstelle Build-Verzeichnisse
if not exist "dist" mkdir dist
if not exist "build" mkdir build

echo 🔨 Erstelle EXE-Dateien...
echo.

REM 1. GUI Hauptanwendung
echo 📋 Erstelle MediaSorter GUI...
pyinstaller --onefile --windowed --name "MediaSorter_GUI" --distpath "./dist" image_sorter_gui.py
if %errorlevel% neq 0 (
    echo ❌ Fehler beim Erstellen der GUI-EXE
    pause
    exit /b 1
)
echo ✅ MediaSorter_GUI.exe erstellt

REM 2. Timeline Viewer
echo 🎭 Erstelle Timeline Viewer...
pyinstaller --onefile --windowed --name "MediaSorter_Timeline" --distpath "./dist" image_timeline_viewer.py
if %errorlevel% neq 0 (
    echo ❌ Fehler beim Erstellen der Timeline-EXE
    pause
    exit /b 1
)
echo ✅ MediaSorter_Timeline.exe erstellt

REM 3. Web Viewer (falls vorhanden)
if exist "image_viewer_web.py" (
    echo 🌐 Erstelle Web Viewer...
    pyinstaller --onefile --name "MediaSorter_WebViewer" --distpath "./dist" --add-data "templates;templates" image_viewer_web.py
    if %errorlevel% neq 0 (
        echo ❌ Fehler beim Erstellen der WebViewer-EXE
    ) else (
        echo ✅ MediaSorter_WebViewer.exe erstellt
    )
)

REM Hash Manager ist jetzt vollständig in die GUI integriert!

echo.
echo ========================================
echo    BUILD ABGESCHLOSSEN! 🎉
echo ========================================
echo.
echo Erstelle EXE-Dateien in ./dist/:
dir /b dist\*.exe
echo.
echo Zum Testen:
echo   - Doppelklick auf MediaSorter_GUI.exe (mit integriertem Hash-Manager)
echo   - Timeline: MediaSorter_Timeline.exe
echo.

REM Cleanup (optional)
echo Möchtest du Build-Dateien löschen? (J/N)
set /p cleanup="Build-Ordner löschen (spart Speicherplatz): "
if /i "%cleanup%"=="J" (
    echo 🧹 Lösche temporäre Build-Dateien...
    rmdir /s /q build 2>nul
    del /q *.spec 2>nul
    echo ✅ Build-Dateien gelöscht
)

echo.
echo ✨ Fertig! Alle Programme sind bereit zur Verwendung.
pause 