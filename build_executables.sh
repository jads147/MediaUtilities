#!/bin/bash

echo "========================================"
echo "    MediaUtils Executable Builder"
echo "========================================"
echo

# Prüfe ob PyInstaller installiert ist
if ! python3 -c "import PyInstaller" 2>/dev/null; then
    echo "❌ ERROR: PyInstaller ist nicht installiert!"
    echo "Installiere mit: pip install pyinstaller"
    exit 1
fi

echo "✅ PyInstaller gefunden"
echo

# Erstelle Build-Verzeichnisse
mkdir -p dist build

echo "🔨 Erstelle ausführbare Dateien..."
echo

# 1. GUI Hauptanwendung
echo "📋 Erstelle MediaSorter GUI..."
pyinstaller --onefile --windowed --name "MediaSorter_GUI" --distpath "./dist" image_sorter_gui.py
if [ $? -ne 0 ]; then
    echo "❌ Fehler beim Erstellen der GUI-Anwendung"
    exit 1
fi
echo "✅ MediaSorter_GUI erstellt"

# 2. Timeline Viewer
echo "🎭 Erstelle Timeline Viewer..."
pyinstaller --onefile --windowed --name "MediaSorter_Timeline" --distpath "./dist" image_timeline_viewer.py
if [ $? -ne 0 ]; then
    echo "❌ Fehler beim Erstellen der Timeline-Anwendung"
    exit 1
fi
echo "✅ MediaSorter_Timeline erstellt"

# 3. Web Viewer (falls vorhanden)
if [ -f "image_viewer_web.py" ]; then
    echo "🌐 Erstelle Web Viewer..."
    pyinstaller --onefile --name "MediaSorter_WebViewer" --distpath "./dist" --add-data "templates:templates" image_viewer_web.py
    if [ $? -eq 0 ]; then
        echo "✅ MediaSorter_WebViewer erstellt"
    else
        echo "❌ Fehler beim Erstellen der WebViewer-Anwendung"
    fi
fi

# Hash Manager ist jetzt vollständig in die GUI integriert!

echo
echo "========================================"
echo "    BUILD ABGESCHLOSSEN! 🎉"
echo "========================================"
echo

echo "Erstelle ausführbare Dateien in ./dist/:"
ls -la dist/MediaSorter_*
echo

echo "Zum Testen:"
echo "  - GUI: ./dist/MediaSorter_GUI (mit integriertem Hash-Manager)"
echo "  - Timeline: ./dist/MediaSorter_Timeline"
echo

# Cleanup (optional)
read -p "Build-Dateien löschen (spart Speicherplatz)? (j/N): " cleanup
if [[ $cleanup =~ ^[Jj]$ ]]; then
    echo "🧹 Lösche temporäre Build-Dateien..."
    rm -rf build
    rm -f *.spec
    echo "✅ Build-Dateien gelöscht"
fi

echo
echo "✨ Fertig! Alle Programme sind bereit zur Verwendung."

# Mache die Dateien ausführbar (für Linux/Mac)
chmod +x dist/MediaSorter_*
echo "✅ Ausführungsrechte gesetzt" 