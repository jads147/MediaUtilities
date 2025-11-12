# 📦 EXE-Erstellung für MediaUtils

Diese Anleitung zeigt, wie du die Python-Dateien zu ausführbaren EXE-Dateien konvertierst.

## 🚀 Schnellstart

### Windows:
```bash
# 1. PyInstaller installieren
pip install pyinstaller

# 2. Automatischen Build starten
build_executables.bat
```

### Linux/Mac:
```bash
# 1. PyInstaller installieren
pip install pyinstaller

# 2. Script ausführbar machen und starten
chmod +x build_executables.sh
./build_executables.sh
```

## 📁 Erstelle EXE-Dateien

Nach erfolgreichem Build findest du im `dist/` Ordner:

```
dist/
├── MediaSorter_GUI.exe          # Hauptanwendung (GUI mit integriertem Hash-Manager 🔢)
├── MediaSorter_Timeline.exe     # Timeline Viewer
└── MediaSorter_WebViewer.exe    # Web Viewer (falls vorhanden)
```

## 🎯 Verwendung der EXE-Dateien

### 📋 MediaSorter_GUI.exe
- **Doppelklick** zum Starten
- Vollständige GUI-Version mit integriertem Hash-Manager 🔢
- Keine Python-Installation nötig
- Alle Features verfügbar
- Hash-Datenbank-Verwaltung direkt in der GUI

### 🎭 MediaSorter_Timeline.exe
- **Doppelklick** zum Starten
- Timeline-Viewer für sortierte Medien
- Interaktive Browsing-Erfahrung



## ⚙️ Build-Optionen

### Einzelne EXE-Dateien erstellen:

```bash
# GUI (eine einzige EXE-Datei)
pyinstaller --onefile --windowed image_sorter_gui.py

# Timeline Viewer
pyinstaller --onefile --windowed image_timeline_viewer.py
```

### Erweiterte Optionen:

```bash
# Mit Icon
pyinstaller --onefile --windowed --icon=icon.ico image_sorter_gui.py

# Kleinere EXE (UPX-Komprimierung)
pyinstaller --onefile --windowed --upx-dir=/path/to/upx image_sorter_gui.py

# Debug-Version (mit Konsole für Fehlersuche)
pyinstaller --onefile image_sorter_gui.py
```

## 🛠️ Troubleshooting

### Problem: "ModuleNotFoundError"
**Lösung**: Füge fehlende Module zur `hiddenimports` Liste hinzu:
```bash
pyinstaller --onefile --hidden-import=missing_module image_sorter_gui.py
```

### Problem: EXE zu groß
**Lösungen**:
1. **UPX-Komprimierung verwenden**:
   ```bash
   # UPX installieren: https://upx.github.io/
   pyinstaller --onefile --upx-dir=/path/to/upx image_sorter_gui.py
   ```

2. **Unnötige Module ausschließen**:
   ```bash
   pyinstaller --onefile --exclude-module=matplotlib --exclude-module=numpy image_sorter_gui.py
   ```

3. **Directory-Build statt --onefile**:
   ```bash
   pyinstaller --windowed image_sorter_gui.py
   # Erstellt Ordner mit mehreren Dateien (schnellerer Start)
   ```

### Problem: EXE startet langsam
**Lösungen**:
1. **Directory-Build verwenden** (schneller als --onefile)
2. **Antivirus-Ausnahme** für den dist/ Ordner hinzufügen
3. **--exclude-module** für große, ungenutzte Bibliotheken

### Problem: PIL/Pillow Fehler
**Lösung**: Explizit hinzufügen:
```bash
pyinstaller --onefile --hidden-import=PIL._tkinter_finder image_sorter_gui.py
```

## 📋 Checklist für Distribution

- [ ] **Testen der EXE-Dateien** auf einem System ohne Python
- [ ] **Antivirus-Scan** (PyInstaller-EXEs werden manchmal fälschlicherweise erkannt)
- [ ] **README.md für Endnutzer** erstellen
- [ ] **Versionsnummer** in Dateinamen einbauen (z.B. `MediaSorter_GUI_v1.1.exe`)
- [ ] **Digitale Signatur** für Vertrauen (optional, kostenpflichtig)

## 🔧 Erweiterte Konfiguration

### Custom .spec Datei verwenden:
```bash
# Erstelle .spec Datei
pyinstaller --onefile image_sorter_gui.py

# Bearbeite image_sorter_gui.spec nach Bedarf
# Dann build mit:
pyinstaller image_sorter_gui.spec
```

### Für alle Programme gleichzeitig:
```bash
pyinstaller build_config.spec
```

## 📊 Dateigrößen (ca.)

| Programm | Einzel-EXE | Directory | Beschreibung |
|----------|------------|-----------|--------------|
| GUI | ~25-40 MB | ~15-25 MB | Vollständige Anwendung + Hash-Manager |
| Timeline | ~20-35 MB | ~10-20 MB | GUI ohne Hash-DB |

## 🎁 Vorteile der EXE-Dateien

✅ **Keine Python-Installation** nötig  
✅ **Einfache Verteilung** (eine Datei)  
✅ **Schnelle Installation** (nur kopieren)  
✅ **Windows-Integration** (Doppelklick zum Starten)  
✅ **Bessere Benutzererfahrung** für Endanwender  

## 🚀 Verbesserungen für zukünftige Versionen

- **Icon erstellen** für professionelles Aussehen
- **Installer** mit NSIS oder Inno Setup
- **Auto-Updater** implementieren
- **Digitale Signatur** für Vertrauen
- **Mehrsprachigkeit** in Build-Scripts

---

**💡 Tipp**: Verwende die automatischen Build-Scripts (`build_executables.bat`/`.sh`) für einfache und konsistente Builds! 