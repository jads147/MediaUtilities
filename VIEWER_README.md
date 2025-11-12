# 🖼️ Medien Viewer Web-App

Eine moderne Web-Anwendung zum Betrachten deiner sortierten Medien (Bilder, Videos, Audio) mit einer wunderschönen, intuitiven Benutzeroberfläche.

## ✨ Features

- **🌐 Web-basiert**: Läuft in deinem Browser - keine Installation nötig
- **📅 Timeline-Ansicht**: Wie Windows-Desktop-Hover - Jahre, Monate, Tage
- **🖼️ Mediengalerie**: Thumbnail-Ansicht mit Vollbild-Modal
- **🎬 Video-Wiedergabe**: Integrierter Video-Player für alle Formate
- **🎵 Audio-Wiedergabe**: Eingebauter Audio-Player
- **📊 Statistiken**: Überblick über deine Mediensammlung
- **🔍 Intelligente Erkennung**: Erkennt automatisch Monats- und Tages-Sortierung
- **📱 Responsive**: Funktioniert auf Desktop, Tablet und Handy
- **⚡ Schnell**: Lazy-Loading für optimale Performance
- **🎨 Modern**: Glasmorphism-Design mit sanften Animationen

## 🚀 Installation

1. **Abhängigkeiten installieren:**
```bash
pip install -r requirements_viewer.txt
```

2. **Starten:**
```bash
# Option 1: Batch-Datei (Windows)
start_viewer.bat

# Option 2: Direkt
python image_viewer_web.py
```

3. **Browser öffnen:**
```
http://127.0.0.1:5000
```

## 📋 Verwendung

### 1. **Ordner auswählen**
- Gib den Pfad zu deinen sortierten Medien ein
- Beispiel: `C:\Sortierte_Medien`
- Klick auf "📁 Laden"

### 2. **Medien durchsuchen**
- **Jahre**: Klick auf Jahr um Monate zu sehen
- **Monate**: Klick auf Monat um Medien zu sehen
- **Tage**: Bei Tages-Sortierung klick auf Tag-Badge

### 3. **Medien betrachten**
- **Thumbnail**: Klick für Vollbild-Ansicht/Wiedergabe
- **Navigation**: Pfeiltasten oder Buttons
- **Schließen**: ESC oder X-Button

## 🎯 Unterstützte Strukturen

### **Monats-Sortierung:**
```
Sortierte_Medien/
├── 2023/
│   ├── 01-January/
│   │   ├── foto1.jpg
│   │   ├── video1.mp4
│   │   └── audio1.mp3
│   └── 02-February/
├── _unknown_date/
└── _duplicates/
```

### **Tages-Sortierung:**
```
Sortierte_Medien/
├── 2023/
│   ├── 01-January/
│   │   ├── 01/
│   │   │   └── foto1.jpg
│   │   └── 15/
│   │       ├── video1.mp4
│   │       └── audio1.mp3
├── _unknown_date/
└── _duplicates/
```

## 🎨 Screenshots

### **Hauptansicht:**
- Moderne Timeline mit Jahren und Monaten
- Statistik-Karten mit Übersicht
- Smooth Hover-Effekte

### **Bildergalerie:**
- Grid-Layout mit Thumbnails
- Dateiname und Größe angezeigt
- Responsive Design

### **Vollbild-Modal:**
- Große Bildansicht
- Navigation zwischen Bildern
- Keyboard-Shortcuts

## ⚡ Performance

- **Lazy Loading**: Bilder werden nur bei Bedarf geladen
- **Thumbnails**: Optimierte Vorschaubilder
- **Caching**: Browser-Cache für bessere Performance
- **Responsive**: Angepasst an Bildschirmgröße

## 🔧 Technische Details

### **Backend:**
- **Flask**: Python Web-Framework
- **Pathlib**: Moderne Dateisystem-Navigation
- **JSON API**: RESTful Schnittstelle

### **Frontend:**
- **Vanilla JavaScript**: Keine Frameworks, pure Performance
- **CSS Grid**: Moderne Layout-Technologie
- **Flexbox**: Responsive Komponenten
- **CSS Animations**: Smooth Transitions

### **Unterstützte Formate:**
- **Bilder**: JPG, JPEG, PNG, TIFF, TIF, BMP, GIF, WEBP
- **Videos**: MP4, AVI, MOV, MKV, WMV, FLV, WEBM, M4V
- **Audio**: MP3, WAV, FLAC, AAC, OGG, M4A, WMA, OPUS

## 🚀 Erweiterte Features

### **Keyboard-Shortcuts:**
- `←/→`: Vorheriges/Nächstes Bild
- `ESC`: Vollbild schließen
- `Enter`: Ordner laden

### **Mobile Optimierung:**
- Touch-Gesten für Navigation
- Responsive Grid-Layout
- Optimierte Thumbnail-Größen

### **Spezielle Bereiche:**
- **Unbekannte Daten**: Bilder ohne erkennbares Datum
- **Duplikate**: Gefundene Duplikate
- **Statistiken**: Überblick über Sammlung

## 🔄 Integration mit Medien Sorter

Der Viewer ist perfekt abgestimmt auf den **Medien Sorter**:

1. **Sortiere** deine Medien mit `image_sorter_gui.py`
2. **Betrachte** sie mit `image_viewer_web.py`
3. **Gleiche Struktur** - nahtlose Integration aller Medientypen

## 🆚 Vergleich: Web vs. Desktop

### **Web-App (Aktuell):**
- ✅ Moderne UI mit Glasmorphism
- ✅ Responsive Design
- ✅ Keine Installation nötig
- ✅ Läuft überall (Windows, Mac, Linux)
- ✅ Einfach zu erweitern

### **Desktop-App (Möglich):**
- ✅ Native Performance
- ✅ Bessere Datei-Integration
- ✅ Offline-Funktionalität
- ❌ Plattform-spezifisch
- ❌ Aufwendigere Entwicklung

## 🎯 Roadmap

### **Phase 1 (Aktuell):**
- ✅ Grundlegende Viewer-Funktionalität
- ✅ Timeline-Navigation
- ✅ Vollbild-Modal

### **Phase 2 (Möglich):**
- 🔄 Slideshow-Modus
- 🔄 Zoom-Funktionalität
- 🔄 Metadaten-Anzeige (EXIF)
- 🔄 Favoriten-System

### **Phase 3 (Erweitert):**
- 🔄 Drag & Drop Upload
- 🔄 Bildbearbeitung (Rotation, etc.)
- 🔄 Sharing-Funktionen
- 🔄 Volltext-Suche

## 💡 Anpassungen

### **Eigene Styles:**
```css
/* In templates/index.html anpassen */
:root {
    --primary-color: #667eea;
    --secondary-color: #764ba2;
}
```

### **Neue Features:**
```python
# In image_viewer_web.py erweitern
@app.route('/api/custom_feature')
def custom_feature():
    # Deine Logik hier
    pass
```

## ⚠️ Hinweise

- **Sicherheit**: Nur für lokale Nutzung gedacht
- **Performance**: Bei >10.000 Bildern evtl. langsamer
- **Browser**: Moderne Browser empfohlen (Chrome, Firefox, Edge)
- **Pfade**: Windows-Pfade mit Backslashes unterstützt

## 🤝 Zusammenfassung

Der **Bilder Viewer** ist die perfekte Ergänzung zum **Bilder Sorter**:

1. **Sortiere** mit der GUI-App
2. **Betrachte** mit der Web-App
3. **Genieße** deine organisierte Bildersammlung!

**Schwierigkeit**: Mittel (3-4 Tage Entwicklung)
**Wartung**: Einfach erweiterbar
**Nutzen**: Sehr hoch - macht sortierte Bilder richtig nutzbar! 