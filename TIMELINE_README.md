# 🎭 Medien Timeline Viewer

Ein interaktiver horizontaler Zeitstrahl-Viewer für deine sortierten Medien (Bilder, Videos, Audio) mit nativer Performance und unbegrenztem Scrolling.

## ✨ Features

- **🕰️ Horizontaler Zeitstrahl**: Natürliche chronologische Navigation
- **🔍 Stufenloser Zoom**: 30% bis 300% mit Mausrad + Ctrl
- **🖼️ Live-Thumbnails**: 4 Vorschaubilder pro Zeitraum
- **🎬 Video-Thumbnails**: Automatische Thumbnail-Generierung für Videos (OpenCV)
- **🎵 Audio-Unterstützung**: Erkennung und Anzeige von Audio-Dateien
- **⚡ Performance**: Lädt Thumbnails asynchron im Hintergrund
- **📅 Intelligente Gruppierung**: Jahre und Monate visuell getrennt
- **🖱️ Intuitive Bedienung**: Klick für Auswahl, Doppelklick für Details
- **🎯 Präzise Navigation**: Horizontales Scrollen mit Mausrad
- **⌨️ Tastaturkürzel**: Pfeiltasten für Navigation
- **📊 Live-Statistiken**: Anzahl Medien und Zeiträume in Echtzeit

## 🚀 Installation & Start

### **Schnellstart:**
```bash
# Doppelklick auf:
start_timeline.bat

# Oder manuell:
python image_timeline_viewer.py
```

### **Voraussetzungen:**
```bash
pip install -r requirements.txt
```

**Abhängigkeiten:**
- `Pillow` (für Thumbnails)
- `tkinter` (GUI - normalerweise bereits enthalten)

## 📋 Verwendung

### **1. Ordner auswählen**
```
📁 Durchsuchen → Wähle deinen sortierten Medien-Ordner
🔄 Laden → Timeline wird erstellt
```

### **2. Navigation**
- **Horizontaler Scroll**: Mausrad
- **Zoom**: Mausrad + Ctrl-Taste
- **Zeitraum auswählen**: Einfacher Klick
- **Medien anzeigen**: Doppelklick oder "🖼️ Bilder anzeigen"

### **3. Zoom-Kontrollen**
- **➕ / ➖ Buttons**: Stufenweises Zoomen
- **Mausrad + Ctrl**: Stufenloses Zoomen
- **100%**: Standardgröße
- **Bereich**: 30% - 300%

## 🎯 Unterstützte Strukturen

### **Monats-Sortierung:**
```
Sortierte_Medien/
├── 2023/
│   ├── 01-January/
│   │   ├── foto1.jpg
│   │   └── video1.mp4
│   └── 02-February/
├── 2024/
│   └── 03-March/
```

### **Tages-Sortierung:**
```
Sortierte_Medien/
├── 2023/
│   ├── 01-January/
│   │   ├── 15/
│   │   │   └── foto1.jpg
│   │   └── 20/
│   │       └── video1.mp4
```

## 🖼️ Unterstützte Medienformate

### **Bilder** (mit Thumbnails):
- JPG, JPEG, PNG, TIFF, TIF
- BMP, GIF, WEBP

### **Videos** (mit Thumbnails):
- MP4, AVI, MOV, MKV, WMV
- FLV, WEBM, M4V, 3GP
- *Benötigt OpenCV für Video-Thumbnails*

### **Audio** (mit Placeholder-Icon):
- MP3, WAV, FLAC, AAC, OGG
- M4A, WMA, OPUS

## 🎨 Timeline-Design

### **Jahre-Header:**
```
┌─ 2023 ──────────────────────┐
│                             │
│ Jan  Feb  Mar  Apr  Mai ... │
│ [4]  [12] [8]  [15] [23]    │
└─────────────────────────────┘
```

### **Monats-Karten:**
```
┌─ January ─────┐
│ [📸] [📸]     │
│ [📸] [📸]     │  ← 4 Thumbnails
│               │
│ 23 Medien     │
└───────────────┘
```

## ⚡ Performance-Optimierungen

### **Asynchrone Thumbnail-Generierung:**
- Thumbnails werden im Hintergrund geladen
- Keine Blockierung der Benutzeroberfläche
- Intelligenter Cache für wiederholte Zugriffe

### **Speicher-Management:**
- Automatische Thumbnail-Größenanpassung
- Cache-Verwaltung für große Sammlungen
- Effiziente Canvas-Rendering

### **Responsive Design:**
- Dynamische Anpassung an Fenstergröße
- Optimierte Scroll-Performance
- Smooth Zoom-Transitions

## 🔧 Tastaturkürzel

| Taste | Aktion |
|-------|--------|
| **Mausrad** | Horizontaler Scroll |
| **Ctrl + Mausrad** | Zoom In/Out |
| **Klick** | Zeitraum auswählen |
| **Doppelklick** | Medien-Viewer öffnen |
| **← / →** | Thumbnail-Navigation |
| **ESC** | Auswahl aufheben |

## 🎯 Anwendungsszenarien

### **1. Große Fotosammlungen:**
```
10,000+ Fotos über 5 Jahre
→ Schnelle Navigation durch chronologische Timeline
→ Sofortige Vorschau durch Thumbnails
```

### **2. Event-Dokumentation:**
```
Hochzeiten, Urlaube, Geburtstage
→ Zeitliche Einordnung auf einen Blick
→ Einfaches Auffinden bestimmter Ereignisse
```

### **3. Professionelle Archivierung:**
```
Business-Fotografie, Dokumentation
→ Chronologische Übersicht aller Projekte
→ Schneller Zugriff auf Zeiträume
```

## 📊 Live-Statistiken

**Info-Panel zeigt:**
- Gesamtzahl der Medien
- Anzahl der Zeiträume
- Aktuell ausgewählter Zeitraum
- Lade-Status

**Beispiel:**
```
1,234 Medien in 48 Zeiträumen
Ausgewählt: January 2024 - 67 Medien
```

## 🔄 Integration mit Medien Sorter

### **Perfekte Zusammenarbeit:**
1. **Sortiere** mit `image_sorter_gui.py` (Medien Sorter)
2. **Betrachte** mit `image_timeline_viewer.py` (Timeline)
3. **Web-View** mit `image_viewer_web.py` (Web-Viewer)

### **Dreifache Ansicht:**
- **Timeline**: Chronologische Übersicht (Desktop)
- **Grid**: Detaillierte Ansicht (Web)
- **Sortierer**: Organisation und Verwaltung aller Medientypen

## 🆚 Vergleich der Viewer

### **Timeline-Viewer (Neu):**
- ✅ Chronologische Navigation
- ✅ Große Sammlungen optimiert
- ✅ Native Performance
- ✅ Intuitive Zeitstrahl-Metapher
- ✅ Zoom und präzises Scrolling

### **Web-Viewer (Bestehend):**
- ✅ Detaillierte Grid-Ansicht
- ✅ Vollbild-Modal
- ✅ Plattformunabhängig
- ✅ Moderne Web-UI

### **Wann welchen Viewer verwenden:**

| Szenario | Timeline-Viewer | Web-Viewer |
|----------|----------------|------------|
| **Chronologische Navigation** | ✅ | ❌ |
| **Große Sammlungen (10k+)** | ✅ | ⚠️ |
| **Schnelle Übersicht** | ✅ | ❌ |
| **Detaillierte Betrachtung** | ❌ | ✅ |
| **Vollbild-Ansicht** | ❌ | ✅ |
| **Mobile Geräte** | ❌ | ✅ |

## 🔧 Technische Details

### **GUI-Framework:**
- **tkinter**: Native Python GUI
- **Canvas**: Hardware-beschleunigtes Rendering
- **Threading**: Asynchrone Thumbnail-Generierung

### **Bildverarbeitung:**
- **Pillow**: Hochqualitative Thumbnail-Generierung
- **LANCZOS**: Optimaler Resize-Algorithmus
- **Aspect Ratio**: Automatische Seitenverhältnis-Erhaltung

### **Performance:**
- **Lazy Loading**: Thumbnails nur bei Bedarf
- **Cache-System**: Intelligente Wiederverwendung
- **Memory Management**: Automatische Speicherfreigabe

## 🚀 Zukünftige Erweiterungen

### **Phase 1 (Möglich):**
- 🔄 Minimap für große Zeiträume
- 🔄 Tooltips mit Medien-Details
- 🔄 Favoriten-Markierung
- 🔄 Suchfunktion nach Datum

### **Phase 2 (Erweitert):**
- 🔄 Video-Thumbnails (erste Frames)
- 🔄 EXIF-Daten-Anzeige
- 🔄 Batch-Operationen
- 🔄 Export-Funktionen

### **Phase 3 (Profi):**
- 🔄 Gesichtserkennung-Integration
- 🔄 KI-basierte Kategorisierung
- 🔄 Cloud-Synchronisation
- 🔄 Kollaborative Features

## 🔧 Anpassungen

### **Timeline-Optionen:**
```python
# In image_timeline_viewer.py anpassen:
self.item_width = 150        # Breite der Zeitraum-Karten
self.item_height = 100       # Höhe der Zeitraum-Karten
self.max_thumbnails = 4      # Anzahl Thumbnails pro Karte
self.thumbnail_size = (80, 60) # Thumbnail-Größe
```

### **Design-Anpassungen:**
```python
# Farben ändern:
canvas_bg = '#34495e'        # Timeline-Hintergrund
year_color = '#3498db'       # Jahre-Header
item_color = '#ecf0f1'       # Monats-Karten
```

## ⚠️ Hinweise

### **Performance:**
- Bei 50+ Jahren evtl. längere Ladezeiten
- Thumbnail-Cache benötigt Speicher
- Große Bilder werden automatisch verkleinert

### **Kompatibilität:**
- Windows: Vollständig unterstützt
- macOS/Linux: Grundfunktionen verfügbar
- Python 3.7+ erforderlich

### **Speicherverbrauch:**
- ~50MB für 1000 Thumbnails
- Automatische Cache-Bereinigung
- Anpassbare Thumbnail-Qualität

## 🤝 Zusammenfassung

Der **Timeline-Viewer** ergänzt perfekt dein Medien-Sortiersystem:

### **Workflow:**
1. **Sortieren** → `image_sorter_gui.py`
2. **Timeline-Übersicht** → `image_timeline_viewer.py` 
3. **Detailansicht** → `image_viewer_web.py`

### **Vorteile:**
- **Intuitive Navigation** durch große Sammlungen
- **Chronologische Orientierung** auf einen Blick
- **Performance** auch bei 10,000+ Medien
- **Native Integration** in dein bestehendes System

**Perfekt für:** Fotografen, Familien-Archive, Event-Dokumentation und alle, die ihre Medien chronologisch erkunden möchten! 📸✨ 