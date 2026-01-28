# MediaUtils

A collection of tools for organizing, sorting, and viewing media files (images, videos, RAW, and audio).

## Features

- **Media Sorter GUI**: Sort media files by date into organized folder structures (Year/Month or Year/Month/Day)
- **Timeline Viewer**: Interactive horizontal timeline for browsing sorted media
- **Media Swiper**: Tinder-style web interface for quick keep/trash sorting
- **Web Viewer**: Browser-based media viewer with calendar navigation

## Supported Formats

| Type | Formats |
|------|---------|
| Images | JPG, JPEG, PNG, GIF, BMP, WEBP, TIFF, HEIC |
| RAW | CR2, CR3, NEF, ARW, DNG, RAF, ORF, RW2, PEF, SRW |
| Video | MP4, AVI, MOV, MKV, WEBM, FLV, M4V, 3GP, MPEG |
| Audio | MP3, WAV, FLAC, AAC, OGG, M4A, WMA, OPUS |

## Requirements

- Python 3.8+
- Dependencies listed in `requirements.txt`

## Installation

1. Clone or download this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Media Sorter GUI

Sorts media files by extracting date information from EXIF metadata or filenames.

```bash
python image_sorter_gui.py
```

Features:
- Copy or Move mode
- Sort by Day or Month
- Dry Run mode for preview
- Duplicate detection via hash database
- Filter by media type

### Timeline Viewer

Visual timeline interface for browsing sorted media collections.

```bash
python image_timeline_viewer.py
```

Features:
- Horizontal timeline navigation
- Thumbnail previews
- Multiple folder support
- Keyboard navigation

### Media Swiper

Web-based swipe interface for quick media sorting decisions.

```bash
python media_swiper.py
```

Features:
- Swipe left (trash) or right (keep)
- Supports sorted folder structures
- Session logging
- Undo functionality

### Web Viewer

Browser-based media viewer for sorted collections.

```bash
python image_viewer_web.py
```

Features:
- Calendar-based navigation
- EXIF data display
- Support for multiple base folders

## Building Executables

To create standalone Windows executables:

```bash
pip install pyinstaller
build_executables.bat
```

This creates the following executables in `./dist/`:
- `MediaSorter_GUI.exe`
- `MediaSorter_Timeline.exe`
- `MediaSorter_WebViewer.exe`
- `MediaSorter_Swiper.exe`

## Languages

The application supports English and German. Language can be changed in each application's interface.

## Support This Project

If you find MediaUtils helpful, consider buying me a coffee:

[![Donate](https://img.shields.io/badge/Donate-PayPal-blue.svg)](https://www.paypal.com/donate?business=callofbeauty247%40gmail.com&currency_code=EUR)

## License

This project is provided as-is for personal use.
