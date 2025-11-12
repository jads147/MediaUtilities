# Medien Sorter

Ein Python-Tool zum automatischen Sortieren von Medien (Bilder, Videos, Audio) nach Jahr/Monat mit intelligenter Duplikat-Erkennung.

## 🖼️ GUI-Version (Empfohlen)

Die neue grafische Benutzeroberfläche macht die Bedienung kinderleicht!

### Schnellstart GUI:
1. Doppelklick auf `start_gui.bat` ODER
2. `python image_sorter_gui.py` im Terminal

## 🎭 Timeline Viewer (Neu!)

Erlebe deine sortierten Medien in einem interaktiven horizontalen Zeitstrahl!

### Schnellstart Timeline:
1. Doppelklick auf `start_timeline.bat` ODER
2. `python image_timeline_viewer.py` im Terminal

### Timeline-Features:
- ✅ **Horizontaler Zeitstrahl** - Chronologische Navigation durch große Sammlungen
- ✅ **Stufenloser Zoom** - 30% bis 300% mit Mausrad + Ctrl
- ✅ **Live-Thumbnails** - 4 Vorschaubilder pro Zeitraum
- ✅ **Performance-optimiert** - Asynchrone Thumbnail-Generierung
- ✅ **Intuitive Bedienung** - Klick für Auswahl, Doppelklick für Details
- ✅ **Native GUI** - Läuft direkt ohne Browser

### GUI-Features:
- ✅ **Benutzerfreundliche Oberfläche** - Keine Kommandozeile nötig
- ✅ **Verschieben/Kopieren Modus** - Wähle ob Originalmedien erhalten bleiben sollen
- ✅ **Monats/Tages-Sortierung** - Sortiere nach Monaten oder einzelnen Tagen
- ✅ **Medientyp-Auswahl** - Wähle zwischen Bildern, Videos und Audio
- ✅ **Testlauf-Modus** - Sieh was passiert, bevor Dateien verarbeitet werden
- ✅ **Live-Log** - Verfolge den Fortschritt in Echtzeit
- ✅ **Ordner-Browser** - Einfache Auswahl von Quell- und Zielordnern
- ✅ **Fortschrittsanzeige** - Sieh wie viele Dateien verarbeitet wurden
- ✅ **Hash-Datenbank** - Verhindert doppelte Verarbeitung bei wiederholten Sortierungen
- ✅ **Datumsvalidierung** - Erkennt unrealistische Daten (einstellbares frühestes Jahr)
- ✅ **Intelligente Datumserkennung** - Verwendet Datei-Metadaten als Fallback
- ✅ **Erweiterte Duplikat-Behandlung** - 3 Modi: aus, verschieben, ignorieren
- ✅ **Turbo-Modus** - Schnellere Duplikaterkennung für große Sammlungen
- ✅ **Unbekannte Daten** - Spezialordner für Dateien ohne erkennbares Datum
- ✅ **Batch-Verarbeitung** - Verarbeitung in 1000er Schritten für große Sammlungen
- ✅ **Detaillierte Logs** - Zeigt vollständiges Datum und Zielpfad für jede Datei
- ✅ **Integrierter Hash-Manager** - Datenbank-Verwaltung direkt in der GUI mit Duplikaterkennung, Suche und Export

## Features

- **Intelligente Datumserkennung**: Erkennt Datum aus verschiedenen Quellen:
  - EXIF-Daten (Aufnahmedatum für Bilder) - höchste Priorität
  - Metadaten (Erstellungsdatum für Videos/Audio)
  - Dateiname-Patterns (verschiedene Formate)
  - Datei-Erstellungsdatum - niedrigste Priorität

- **Duplikat-Erkennung**: Findet identische Medien basierend auf MD5-Hash

- **Unterstützte Formate**: 
  - **Bilder**: JPG, JPEG, PNG, TIFF, TIF, BMP, GIF, WEBP
  - **Videos**: MP4, AVI, MOV, MKV, WMV, FLV, WEBM, M4V, 3GP
  - **Audio**: MP3, WAV, FLAC, AAC, OGG, M4A, WMA, OPUS

- **Sicherheit**: Dry-Run Modus zum Testen ohne Dateien zu verschieben

- **Logging**: Detaillierte Protokollierung aller Aktionen

### **📋 Beispiel Log-Ausgabe:**

**Mit aktivierter Duplikat-Behandlung:**
```
🔍 Suche nach Duplikaten...
📁 Behandle Duplikate...
Duplikat verschoben: IMG_copy.jpg -> _duplicates/IMG_copy_1.jpg

📂 Sortiere Bilder...
Kopiert (EXIF) [2023-12-25]: IMG_20231225_142530.jpg -> 2023/12-December/IMG_20231225_142530.jpg
Kopiert (FILENAME) [2023-01-15]: vacation_20230115.png -> 2023/01-January/vacation_20230115.png
Kopiert (METADATA) [2024-03-01]: photo_edit.jpg -> 2024/03-March/photo_edit.jpg
Kopiert (unrealistisches Datum): old_scan_1999.jpg -> _invalid_date/
Kopiert (unbekanntes Datum): screenshot.png -> _unknown_date/
Übersprungen (bereits in DB): already_sorted.jpg

✅ Sortierung erfolgreich abgeschlossen!
```

**Mit deaktivierter Duplikat-Behandlung:**
```
Duplikat-Suche übersprungen (deaktiviert)
Duplikat-Behandlung übersprungen (deaktiviert)

📂 Sortiere Bilder...
Kopiert (EXIF) [2023-12-25]: IMG_20231225_142530.jpg -> 2023/12-December/IMG_20231225_142530.jpg
Kopiert (EXIF) [2023-12-25]: IMG_20231225_copy.jpg -> 2023/12-December/IMG_20231225_copy.jpg
Kopiert (FILENAME) [2023-01-15]: vacation_20230115.png -> 2023/01-January/vacation_20230115.png

✅ Sortierung erfolgreich abgeschlossen!
```

**Mit aktivierter Batch-Verarbeitung:**
```
Verarbeite 12,500 Dateien...
Batch-Verarbeitung aktiviert: 1000 Dateien pro Durchgang

🔍 Suche nach Duplikaten...
📁 Behandle Duplikate...

📦 Batch 1/13 - 1000 Dateien
Kopiert (EXIF) [2023-12-25]: IMG_20231225_142530.jpg -> 2023/12-December/IMG_20231225_142530.jpg
Kopiert (FILENAME) [2023-01-15]: vacation_20230115.png -> 2023/01-January/vacation_20230115.png
...

📦 Batch 2/13 - 1000 Dateien
Kopiert (METADATA) [2024-03-01]: photo_edit.jpg -> 2024/03-March/photo_edit.jpg
...

📦 Batch 13/13 - 500 Dateien
Kopiert (EXIF) [2024-11-30]: final_photo.jpg -> 2024/11-November/final_photo.jpg

✅ Sortierung erfolgreich abgeschlossen!
```

## Installation

### Option 1: EXE-Dateien (Empfohlen für Endnutzer)
Keine Python-Installation nötig! Direkt ausführbare Programme:

1. **EXE-Dateien erstellen**:
```bash
# Installiere PyInstaller
pip install pyinstaller

# Windows: Automatischer Build
build_executables.bat

# Linux/Mac: Automatischer Build
chmod +x build_executables.sh
./build_executables.sh
```

2. **Programme aus ./dist/ Ordner verwenden**:
   - `MediaSorter_GUI.exe` - Hauptanwendung (mit integriertem Hash-Manager 🔢)
   - `MediaSorter_Timeline.exe` - Timeline Viewer

📖 **Detaillierte Anleitung**: Siehe [BUILD_EXECUTABLE_README.md](BUILD_EXECUTABLE_README.md)

### Option 2: Python-Installation
1. Python 3.7+ installieren
2. Abhängigkeiten installieren:
```bash
pip install -r requirements.txt
```

## Verwendung

### Empfohlene Verwendung (GUI)
```bash
# Starte die grafische Oberfläche
python image_sorter_gui.py

# Oder verwende die Batch-Datei
start_gui.bat
```

### Kommandozeilen-Verwendung (falls verfügbar)
```bash
# Hinweis: Kommandozeilen-Version muss separat implementiert werden
# Die GUI-Version ist die Hauptanwendung
```

## Ordnerstruktur

### 📅 Monats-Sortierung (Standard):
```
Zielordner/
├── 2023/
│   ├── 01-January/
│   │   ├── IMG_20230115_142530.jpg
│   │   └── photo_2023-01-20.png
│   └── 02-February/
│       └── vacation_20230205.jpg
├── 2024/
│   └── 03-March/
│       └── IMG_20240301_120000.jpg
├── _unknown_date/
│   ├── screenshot.png
│   └── photo_bearbeitet.jpg
├── _invalid_date/
│   ├── IMG_19990101_error.jpg  (vor 2004)
│   └── future_photo_2030.png   (Zukunftsdatum)
├── _duplicates/
│   ├── duplicate_1.jpg
│   └── duplicate_2.jpg
├── sort_report.txt
└── image_sorter.log
```

### 📆 Tages-Sortierung:
```
Zielordner/
├── 2023/
│   ├── 01-January/
│   │   ├── 15/
│   │   │   └── IMG_20230115_142530.jpg
│   │   └── 20/
│   │       └── photo_2023-01-20.png
│   └── 02-February/
│       └── 05/
│           └── vacation_20230205.jpg
├── 2024/
│   └── 03-March/
│       └── 01/
│           └── IMG_20240301_120000.jpg
├── _unknown_date/
├── _invalid_date/
├── _duplicates/
├── sort_report.txt
└── image_sorter.log
```

## Datumserkennung

Das Tool erkennt Datum in folgender Priorität:

1. **EXIF-Daten** (am genauesten, wenn realistisch)
   - DateTime, DateTimeOriginal, DateTimeDigitized
   - Wird validiert: muss zwischen 2004 und heute liegen

2. **Dateiname-Patterns** (wenn realistisch)
   - `2023-12-25` (YYYY-MM-DD)
   - `20231225` (YYYYMMDD)
   - `25.12.2023` (DD.MM.YYYY)
   - `25-12-2023` (DD-MM-YYYY)
   - `IMG_20231225` (IMG_YYYYMMDD)
   - `2023-12` (YYYY-MM)
   - `202312` (YYYYMM)
   - Wird validiert: muss zwischen 2004 und heute liegen
   - **Nur Dateinamen werden analysiert** (Ordnernamen werden ignoriert)

3. **Datei-Metadaten** (Erstellungs- und Änderungsdatum)
   - Verwendet das frühere der beiden Daten
   - Windows: Echtes Erstellungsdatum vs. Änderungsdatum
   - Unix/Mac: Verwendet beste verfügbare Metadaten
   - Wird validiert: muss zwischen 2004 und heute liegen

4. **Fallback** (wenn alle Daten unrealistisch/nicht vorhanden)
   - Aktuelles Datum

### **🔍 Datumsvalidierung**

**Warum Validierung?**
- Digitalkameras wurden erst ab 2004 weit verbreitet
- Daten vor 2004 sind meist Systemfehler
- Daten in der Zukunft sind offensichtlich falsch

**Was passiert bei ungültigen Daten?**
- **Unrealistische EXIF-Daten**: Werden ignoriert, nächste Quelle wird versucht
- **Unrealistische Dateinamen**: Werden ignoriert, Datei-Metadaten werden verwendet
- **Alle Daten unrealistisch**: Datei landet in `_invalid_date/` Ordner

**Spezialordner:**
- `_unknown_date/`: Keine Daten gefunden
- `_invalid_date/`: Nur unrealistische Daten gefunden (vor 2004/nach heute)

## Duplikat-Behandlung

- Duplikate werden basierend auf MD5-Hash erkannt
- Erste Datei wird behalten und normal sortiert
- Weitere Duplikate werden in `_duplicates/` Ordner verschoben
- Alle Duplikate werden im Bericht dokumentiert

### **🎛️ Duplikat-Kontrolle**

**Duplikat-Behandlung aktiviert (Standard):**
- ✅ Duplikate werden automatisch erkannt und verschoben
- ✅ Nur ein Exemplar jedes Bildes wird normal sortiert
- ✅ Duplikate landen im `_duplicates/` Ordner
- ✅ Bessere Übersicht, keine doppelten Bilder

**Duplikat-Behandlung deaktiviert:**
- ⚪ Alle Bilder werden normal sortiert (auch Duplikate)
- ⚪ Keine automatische Duplikat-Erkennung
- ⚪ Schnellere Verarbeitung bei großen Sammlungen
- ⚪ Nützlich wenn Duplikate gewünscht sind (z.B. verschiedene Bearbeitungen)

## 📦 Batch-Verarbeitung

### **🚀 Für große Bildsammlungen optimiert**

**Standard-Verarbeitung:**
- Alle Bilder werden in einem Durchgang verarbeitet
- Geeignet für Sammlungen bis ~5,000 Bilder
- Kontinuierliche Verarbeitung ohne Unterbrechung

**Batch-Verarbeitung (1000er Schritte):**
- ✅ **Speicher-schonend**: Verarbeitet nur 1000 Bilder gleichzeitig
- ✅ **Responsive GUI**: Bessere Reaktionszeit bei großen Sammlungen
- ✅ **Fortschritts-Kontrolle**: Zeigt Batch-Fortschritt (z.B. "Batch 3/15")
- ✅ **Unterbrechen möglich**: Stopp-Taste funktioniert zwischen Batches
- ✅ **Speicher-Cleanup**: Automatische Bereinigung zwischen Batches

### **💡 Wann Batch-Verarbeitung verwenden?**

#### **✅ Batch-Verarbeitung AKTIVIEREN für:**
- 📁 **Große Sammlungen**: 10,000+ Bilder
- 💾 **Begrenzte RAM**: Computer mit wenig Arbeitsspeicher
- 🖥️ **GUI-Responsivität**: GUI soll während Verarbeitung reaktionsfähig bleiben
- ⏹️ **Kontrolle**: Möglichkeit zum Stoppen zwischen Batches

#### **⚪ Standard-Verarbeitung für:**
- 📸 **Normale Sammlungen**: Unter 5,000 Bilder
- 🚀 **Maximale Geschwindigkeit**: Kontinuierliche Verarbeitung ohne Pausen
- 💪 **Leistungsstarke Hardware**: Viel RAM und schnelle CPU

### **📊 Batch-Verarbeitung in Aktion:**

```
Verarbeite 12,500 Dateien...
Batch-Verarbeitung aktiviert: 1000 Dateien pro Durchgang

📦 Batch 1/13 - 1000 Dateien
Verarbeite Datei 1: IMG_001.jpg
Verarbeite Datei 500: IMG_500.jpg
Verarbeite Datei 1000: IMG_1000.jpg

📦 Batch 2/13 - 1000 Dateien
Verarbeite Datei 1001: IMG_1001.jpg
...

📦 Batch 13/13 - 500 Dateien
Verarbeite Datei 12001: IMG_12001.jpg
Verarbeite Datei 12500: IMG_12500.jpg

✅ Sortierung erfolgreich abgeschlossen!
```

### **⚡ Performance-Vorteile:**

| Sammlung | Standard | Batch-Modus |
|----------|----------|-------------|
| 1,000 Bilder | ✅ Optimal | ⚪ Nicht nötig |
| 5,000 Bilder | ✅ Gut | ✅ Sicherer |
| 10,000 Bilder | ⚠️ Langsam | ✅ Optimal |
| 50,000+ Bilder | ❌ Problematisch | ✅ Empfohlen |

## Sicherheit

- **Dry-Run Modus**: Teste das Tool zuerst mit `--dry-run`
- **Backup**: Erstelle vorher ein Backup deiner Bilder
- **Logging**: Alle Aktionen werden protokolliert
- **Bericht**: Detaillierter Bericht über alle Änderungen

## 🚀 GUI-Workflow (Empfohlen)

1. **Starte die GUI**:
   - Doppelklick auf `start_gui.bat`

2. **Ordner auswählen**:
   - **Quellordner**: Wähle den Ordner mit deinen Bildern
   - **Zielordner**: Wähle wo die sortierten Bilder hin sollen

3. **Modus wählen**:
   - 📁 **Verschieben**: Originalbilder werden verschoben (Standard)
   - 📋 **Kopieren**: Originalbilder bleiben erhalten (wie Backup)

4. **Sortierung wählen**:
   - 📅 **Nach Monaten**: 2023/01-January/ (Standard)
   - 📆 **Nach Tagen**: 2023/01-January/15/

5. **Optionen einstellen**:
   - ✅ **Testlauf** (für ersten Durchgang aktivieren)
   - ⚪ **Ausführliche Ausgabe** (optional)
   - ✅ **Hash-Datenbank verwenden** (für zukünftige Sortierungen)
   - ✅ **Datumsvalidierung** (unrealistische Daten vor 2004/nach heute erkennen)
   - ✅ **Duplikate verschieben** (identische Bilder automatisch in _duplicates/ Ordner)
   - ⚪ **Batch-Verarbeitung** (1000 Bilder pro Durchgang für große Sammlungen)

6. **Sortierung starten**:
   - Klick auf "🚀 Sortierung starten"
   - Verfolge den Fortschritt im Log-Fenster

7. **Ergebnis prüfen**:
   - Erfolgsmeldung mit Statistiken
   - Sortierte Bilder im Zielordner
   - Duplikate im `_duplicates/` Unterordner
   - Dateien ohne erkennbares Datum im `_unknown_date/` Ordner
   - Dateien mit unrealistischen Daten im `_invalid_date/` Ordner

8. **Hash-Datenbank verwalten** (optional):
   - Klick auf "🔢 Hash-Datenbank verwalten"
   - Statistiken anzeigen und aktualisieren
   - Duplikate in der Datenbank durchsuchen
   - Dateien nach Namen oder Datum suchen
   - Nicht existierende Dateien aufräumen
   - Datenbank zu CSV exportieren

## 📋 Kopier-Modus vs. Verschieben-Modus

### 📁 **Verschieben-Modus (Standard)**
- Originalbilder werden **verschoben** (nicht kopiert)
- Quellordner wird **leer** nach der Sortierung
- **Schneller** und **platzsparender**
- Für finale Sortierung

### 📋 **Kopier-Modus**
- Originalbilder **bleiben erhalten**
- Quellordner bleibt **unverändert**
- Funktioniert wie **automatisches Backup**
- Für Tests oder wenn du Originale behalten willst

**Tipp**: Verwende erst **Kopier-Modus** zum Testen, dann **Verschieben-Modus** für die finale Sortierung!

## Troubleshooting

### Häufige Probleme

1. **"Keine EXIF-Daten"**: Normal für Screenshots oder bearbeitete Bilder
2. **"Datei existiert bereits"**: Tool fügt automatisch Nummerierung hinzu
3. **Fehler beim Öffnen**: Überprüfe Dateiberechtigungen

### Log-Dateien

- `image_sorter.log`: Detaillierte Protokollierung
- `sort_report.txt`: Zusammenfassung der Sortierung

## Erweiterte Optionen

### Eigene Dateiname-Patterns hinzufügen

Du kannst das Script anpassen, um eigene Datum-Patterns zu erkennen:

```python
# In der __init__ Methode der ImageSorter Klasse
self.date_patterns = [
    # Bestehende Patterns...
    r'Foto_(\d{4})_(\d{2})_(\d{2})',  # Foto_YYYY_MM_DD
    # Weitere eigene Patterns...
]
```

### Andere Bildformate unterstützen

```python
# In der __init__ Methode
self.supported_formats = {
    '.jpg', '.jpeg', '.png', '.tiff', '.tif', 
    '.bmp', '.gif', '.webp', '.raw', '.cr2'  # Weitere Formate
}
```

## ⚠️ Wichtige Hinweise

- **Teste immer zuerst** mit "Testlauf" aktiviert
- **Verwende Kopier-Modus** für erste Tests
- **Überprüfe Ergebnisse** bevor du finale Sortierung machst
- **Duplikate** werden automatisch in `_duplicates/` Ordner verschoben
- **Dateien ohne erkennbares Datum** landen in `_unknown_date/` Ordner
- **Dateien mit unrealistischen Daten** (vor 2004/nach heute) landen in `_invalid_date/` Ordner
- **Datumsvalidierung** kann in den Optionen deaktiviert werden (für spezielle Fälle)
- **Hash-Datenbank** spart Zeit bei wiederholten Sortierungen großer Sammlungen 