# PAGASA PDF Annotation Tool - Visual Documentation (2025)

**Generated:** January 5, 2026  
**Version:** Current (Active)  
**Application:** `pdf_annotation_gui.py` (922 lines)

---

## 1. APPLICATION INTERFACE LAYOUT

### Overall Window Structure
```
┌─────────────────────────────────────────────────────────────────────────┐
│  📄 PAGASA PDF Annotation Tool                        File X of Y: ...  │  ← Top Bar (Dark: #2c3e50)
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────────────┐  ┌──────────────────────────────────┐ │
│  │                              │  │                                  │ │
│  │   PDF VIEWER                 │  │   JSON EDITOR                    │ │
│  │   (Left Pane)                │  │   (Right Pane)                   │ │
│  │                              │  │                                  │ │
│  │  • Page display              │  │  • JSON text editor              │ │
│  │  • Navigation (prev/next page)│  │  • Real-time validation         │ │
│  │  • Zoom controls             │  │  • Status indicator              │ │
│  │  • Text selection & copy     │  │  • Auto-scrolling                │ │
│  │                              │  │                                  │ │
│  └──────────────────────────────┘  └──────────────────────────────────┘ │
│         ▲ Resizable split (drag)         ▲ Resizable split (drag)       │
├──────────────────────────────────────────────────────────────────────────┤
│  Ready - Please select a folder                                         │  ← Progress Label
│  ████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░                              │  ← Progress Bar
│  ☐ Auto-analyze next PDF after Save & Next                              │  ← Checkbox
├──────────────────────────────────────────────────────────────────────────┤
│  [📁 Folder] [◀ Previous] [🔍 Analyze] [💾 Save & Next] [Next ▶] [❌Quit] │ ← Navigation (Light: #ecf0f1)
└─────────────────────────────────────────────────────────────────────────┘

Window Size: 1400px × 900px
```

---

## 2. TOP NAVIGATION BAR

```
┌────────────────────────────────────────────────────────┐
│ 📄 PAGASA PDF Annotation Tool    File 15 of 87: ...   │
└────────────────────────────────────────────────────────┘

Background: Dark (#2c3e50)
Text: White
Height: 40px

Left:  Title with icon
Right: File counter (auto-updating)
```

### File Counter Format
```
"File X of Y: filename.pdf"

Examples:
- "File 1 of 87: PAGASA_22-TC08_Henry_TCA#01.pdf"
- "File 15 of 87: PAGASA_22-TC08_Henry_TCB#05.pdf"
- "File 0 of 0: (No PDFs loaded)"
```

---

## 3. SPLIT VIEW LAYOUT

### PDF Viewer (Left Pane - 40-50% width)

```
┌─────────────────────────────────┐
│  PDF Page Display Area          │
│                                 │
│  ┌─────────────────────────────┐│
│  │                             ││
│  │   [Page Image Rendered]     ││  ← Current zoom level × 1.0
│  │                             ││
│  │   (Can select text here)    ││
│  │   (Text copied to clipboard)││
│  └─────────────────────────────┘│
│                                 │
├─────────────────────────────────┤
│ Page 1 of N   |  [🔍-] [Reset] [🔍+]  │
│              Zoom: 100%               │
├─────────────────────────────────┤
│ [◀ Prev Page] [Next Page ▶]     │
└─────────────────────────────────┘

Min Width: 400px
Background: White/Light gray
```

#### Zoom Controls
```
Layout: [🔍- (Zoom Out)] [Reset] [🔍+ (Zoom In)]  Zoom: XXX%

Range:     25% to 300%
Default:   100%
Step:      25% per click
Behavior:  • Saved across PDF navigation
           • Persists for entire session
           • Reset button available
```

#### Page Navigation
```
[◀ Prev Page]  Page X of N  [Next Page ▶]

• Only enabled when PDF has multiple pages
• Updates automatically
• Keyboard support (arrows)
```

#### Text Selection Feature
```
Click & Drag → Blue selection rectangle appears
              Text becomes selectable
              
Copy button or Ctrl+C → Text copied to clipboard

Supports: Single page text selection
```

---

### JSON Editor (Right Pane - 40-50% width)

```
┌──────────────────────────────────┐
│  Extracted Typhoon Data (JSON)   │
│                                  │
│  ┌──────────────────────────────┐│
│  │ {                            ││
│  │   "typhoon_location_text":   ││
│  │     "575 km East of ...",    ││
│  │   "typhoon_movement":        ││
│  │     "West northwestward...", ││
│  │   "updated_datetime":        ││
│  │     "2022-11-17 10:30:00",   ││
│  │   "signal_warning_tags1": {  ││
│  │     "Luzon": "Batanes, ...", ││
│  │     "Visayas": null,         ││
│  │     "Mindanao": null         ││
│  │   }                          ││
│  │   ... (more fields)          ││
│  │ }                            ││
│  │                              ││
│  │ (Editable text area)         ││
│  │ (Scrollable)                 ││
│  │                              ││
│  └──────────────────────────────┘│
├──────────────────────────────────┤
│ ✓ Valid JSON             [fg:green] │  ← Status Indicator
│ ✗ Invalid JSON: line 5... [fg:red]  │
│ (Empty when cleared)     [fg:black]  │
└──────────────────────────────────┘

Min Width: 400px
Background: White
Font: Monospace
```

#### Status Indicator States
```
✓ Valid JSON            [Green]   → Data can be saved
✗ Invalid JSON: ...     [Red]     → Shows error location
(No status shown)       [Black]   → Editor is empty
```

#### JSON Fields (Auto-extracted)
```
{
  "typhoon_location_text": "575 km East of Catarman, Northern Samar...",
  "typhoon_movement": "West northwestward at 30 km/h",
  "typhoon_windspeed": "Maximum sustained winds of 150 km/h near the center...",
  "updated_datetime": "2022-11-17 10:30:00",
  
  "signal_warning_tags1": { "Luzon": "...", "Visayas": null, "Mindanao": null, "Other": null },
  "signal_warning_tags2": { "Luzon": "...", "Visayas": "...", "Mindanao": null, "Other": null },
  "signal_warning_tags3": { "Luzon": null, "Visayas": "...", "Mindanao": "...", "Other": null },
  "signal_warning_tags4": { "Luzon": null, "Visayas": null, "Mindanao": "...", "Other": null },
  "signal_warning_tags5": { "Luzon": null, "Visayas": null, "Mindanao": null, "Other": null },
  
  "rainfall_warning_tags1": { "Luzon": "...", "Visayas": "...", "Mindanao": "...", "Other": null },
  "rainfall_warning_tags2": { "Luzon": "...", "Visayas": null, "Mindanao": null, "Other": null },
  "rainfall_warning_tags3": { "Luzon": null, "Visayas": "...", "Mindanao": null, "Other": null }
}
```

---

## 4. BOTTOM CONTROL BAR

### Progress Status Area
```
┌──────────────────────────────────────────────┐
│ Ready - Please select a folder               │  ← Progress Label
│ ████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░     │  ← Progress Bar
│ ☐ Auto-analyze next PDF after Save & Next   │  ← Checkbox
└──────────────────────────────────────────────┘

Height: ~110px
Background: Light (#ecf0f1)
```

#### Progress Messages

```
"Ready - Please select a folder"              → Waiting for folder selection
"Initializing extractor..."                   → Loading ML models
"Extractor ready"                             → Ready to analyze
"Loaded X PDFs from folder"                   → PDFs loaded
"PDF loaded - Click 'Analyze' to extract..."  → Waiting for user action
"Analyzing PDF... 0%"                         → Processing (w/ progress bar)
"Analysis complete!"                          → Extraction done
"Saved to: dataset/pdfs_annotation/..."       → Annotation saved
"Auto-analyzing..."                           → Auto-analyze running
```

#### Auto-Analyze Checkbox
```
☐ Auto-analyze next PDF after Save & Next

When checked:
  • After clicking "Save & Next"
  • Automatically moves to next PDF
  • Automatically runs "Analyze"
  • Saves time for batch processing

When unchecked:
  • "Save & Next" moves to next PDF only
  • User must click "Analyze" manually
```

---

### Navigation Buttons

```
┌─────────────────────────────────────────────────────────────────┐
│ [📁 Select]  [◀ Prev]  [🔍 Analyze]  [💾 Save & Next]  [Next ▶] [❌Quit] │
└─────────────────────────────────────────────────────────────────┘

Button Heights: 2 rows each
Button Font: Arial, 10pt
Padding: 5px between buttons
```

#### Button Details

```
┌─────────────────────┐
│  📁 Select Folder   │  Color: Gray (#95a5a6)
│                     │  Width: 130px
│  (Text: white)      │  Function: Open folder picker dialog
└─────────────────────┘
         ↓ Opens → "Select Folder with PDFs" dialog
           ↓ Initial dir: dataset/pdfs/ (if exists)
```

```
┌─────────────────────┐
│  ◀ Previous         │  Color: Default (Gray background)
│                     │  Width: 120px
│  (Text: black)      │  Function: Load previous PDF
└─────────────────────┘
         ↓ Disabled if at index 0
```

```
┌─────────────────────┐
│  🔍 Analyze         │  Color: Orange (#e67e22)
│                     │  Width: 120px
│  (Text: white)      │  Function: Extract data from current PDF
│  (Bold font)        │  Spawns background thread
└─────────────────────┘
         ↓ Shows "Analyzing..." with progress bar
         ↓ Disables while processing
```

```
┌─────────────────────┐
│  💾 Save & Next     │  Color: Blue (#3498db)
│                     │  Width: 150px
│  (Text: white)      │  Function: Save JSON annotation + move to next
│  (Bold font)        │  Validates JSON before saving
└─────────────────────┘
         ↓ If auto-analyze checked:
           Auto-analyze next immediately
         ↓ Saves to: dataset/pdfs_annotation/...
```

```
┌─────────────────────┐
│  Next ▶             │  Color: Default (Gray background)
│                     │  Width: 120px
│  (Text: black)      │  Function: Load next PDF
└─────────────────────┘
         ↓ Disabled if at last index
```

```
┌─────────────────────┐
│  ❌ Quit            │  Color: Default (Gray background)
│                     │  Width: 100px
│  (Text: black)      │  Function: Close application
└─────────────────────┘
         ↓ Prompts: "Are you sure?"
```

---

## 5. WORKFLOW DIAGRAM

### Typical User Workflow

```
        START
          ↓
    [📁 Select Folder]
          ↓
    Load PDF List
          ↓
    Display First PDF
          ↓
    ┌─────────────────────────────────────┐
    │                                     │
    │  ┌─────────────────────────────┐   │
    │  │ View PDF                    │   │
    │  │ • Zoom in/out               │   │
    │  │ • Select & copy text        │   │
    │  │ • Navigate pages            │   │
    │  └─────────────────────────────┘   │
    │            ↓                        │
    │  ┌─────────────────────────────┐   │
    │  │ [🔍 Analyze]                │   │
    │  │ • Extracts data from PDF    │   │
    │  │ • Auto-fills JSON editor    │   │
    │  └─────────────────────────────┘   │
    │            ↓                        │
    │  ┌─────────────────────────────┐   │
    │  │ Edit JSON (if needed)       │   │
    │  │ • Manual corrections        │   │
    │  │ • Real-time validation      │   │
    │  └─────────────────────────────┘   │
    │            ↓                        │
    │  ┌─────────────────────────────┐   │
    │  │ [💾 Save & Next]            │   │
    │  │ • Validates JSON            │   │
    │  │ • Saves annotation          │   │
    │  │ • Moves to next PDF         │   │
    │  │ • Auto-analyzes (if set)    │   │
    │  └─────────────────────────────┘   │
    │            ↓                        │
    │    More PDFs?                      │
    │    YES ↙        ↖ NO               │
    │    ↓             ↓                 │
    └────────┼─────────────────────┘     │
             ↓                           │
        (Repeat)                    [❌ Quit]
                                        ↓
                                      END
```

---

## 6. DIALOG WINDOWS

### Folder Selection Dialog

```
┌─────────────────────────────────────┐
│  Select Folder with PDFs            │
│                                     │
│  [Home] [Desktop] [Documents] [+]   │
│                                     │
│  📁 dataset                         │
│    📁 pdfs           ← Usually here │
│      📄 pagasa-*.pdf (38 files)     │
│    📁 pdfs_annotation (output)      │
│                                     │
│  Folder: /path/to/dataset/pdfs      │
│                                     │
│  [Cancel]              [Select]     │
└─────────────────────────────────────┘

Features:
• Initial dir: dataset/pdfs/ (if exists)
• Falls back to current working directory
• Recursively finds all *.pdf files
• Counts total PDFs found
```

---

## 7. COLOR SCHEME

```
Component              Color         Hex      Purpose
─────────────────────────────────────────────────────────
Top Bar Background     Dark Blue     #2c3e50  Professional header
Top Bar Text           White         #FFFFFF  Contrast
Bottom Bar Background  Light Gray    #ecf0f1  Neutral footer

Button (Primary)       Blue          #3498db  "Save & Next" action
Button (Secondary)     Orange        #e67e22  "Analyze" action
Button (Tertiary)      Gray          #95a5a6  "Folder" selection
Button (Default)       Light Gray    #AAA     Other navigation

Status Valid           Green         #00AA00  JSON valid
Status Invalid         Red           #FF0000  JSON error
Status Neutral         Black         #000000  Normal text

PDF Canvas            White/Gray    #FFFFFF  Display area
JSON Editor           White         #FFFFFF  Edit area
Text Selection        Light Blue    #B3D9FF  Visual feedback
```

---

## 8. ANNOTATION OUTPUT STRUCTURE

### File Organization

```
dataset/
├── pdfs/                                    ← Input PDFs
│   ├── pagasa-20-19W/
│   │   ├── PAGASA_20-19W_Pepito_SWB#01.pdf
│   │   ├── PAGASA_20-19W_Pepito_SWB#02.pdf
│   │   └── PAGASA_20-19W_Pepito_SWB#03.pdf
│   ├── pagasa-21-TC04/
│   │   ├── PAGASA_21-TC04_Jolina_TCA#01.pdf
│   │   └── PAGASA_21-TC04_Jolina_TCA#02.pdf
│   └── ... (more folders)
│
└── pdfs_annotation/                         ← Output annotations
    ├── pagasa-20-19W/                      ← Mirrored structure
    │   ├── PAGASA_20-19W_Pepito_SWB#01.json
    │   ├── PAGASA_20-19W_Pepito_SWB#02.json
    │   └── PAGASA_20-19W_Pepito_SWB#03.json
    ├── pagasa-21-TC04/
    │   ├── PAGASA_21-TC04_Jolina_TCA#01.json
    │   └── PAGASA_21-TC04_Jolina_TCA#02.json
    └── ... (more folders)
```

### Annotation File Example

```json
{
  "typhoon_location_text": "575 km East of Catarman, Northern Samar or 620 km East of Virac, Catanduanes",
  "typhoon_movement": "West northwestward at 30 km/h",
  "typhoon_windspeed": "Maximum sustained winds of 150 km/h near the center, gustiness of up to 185 km/h, and central pressure of 955 hPa",
  "updated_datetime": "2022-11-17 10:30:00",
  "signal_warning_tags1": {
    "Luzon": "Batanes, Cagayan, Apayao, Ilocos Norte, Ilocos Sur",
    "Visayas": null,
    "Mindanao": null,
    "Other": null
  },
  "signal_warning_tags2": {
    "Luzon": "Nueva Vizcaya, Quirino, Aurora, Nueva Ecija, Bulacan, Metro Manila",
    "Visayas": "Northern Samar, Eastern Samar, Samar",
    "Mindanao": null,
    "Other": null
  },
  "signal_warning_tags3": {
    "Luzon": null,
    "Visayas": "Leyte, Southern Leyte, Cebu, Bohol, Negros Oriental",
    "Mindanao": "Agusan del Norte, Surigao del Norte, Dinagat Islands",
    "Other": null
  },
  "signal_warning_tags4": {
    "Luzon": null,
    "Visayas": null,
    "Mindanao": "Surigao del Sur",
    "Other": null
  },
  "signal_warning_tags5": {
    "Luzon": null,
    "Visayas": null,
    "Mindanao": null,
    "Other": null
  },
  "rainfall_warning_tags1": {
    "Luzon": "Batanes, Cagayan, Ilocos Norte, Eastern Samar",
    "Visayas": "Northern Samar, Eastern Samar",
    "Mindanao": "Surigao del Norte, Dinagat Islands",
    "Other": null
  },
  "rainfall_warning_tags2": {
    "Luzon": "Apayao, Nueva Vizcaya, Quirino",
    "Visayas": "Samar, Leyte",
    "Mindanao": "Agusan del Norte",
    "Other": null
  },
  "rainfall_warning_tags3": {
    "Luzon": null,
    "Visayas": "Bohol, Cebu",
    "Mindanao": null,
    "Other": null
  }
}
```

---

## 9. KEYBOARD SHORTCUTS

```
Function                Keyboard Shortcut
────────────────────────────────────────
Copy Selected Text      Ctrl+C (in PDF viewer)
Next Page (PDF)         Right Arrow
Previous Page (PDF)     Left Arrow
Zoom In (PDF)           Ctrl+Plus or Scroll Up
Zoom Out (PDF)          Ctrl+Minus or Scroll Down
Zoom Reset (PDF)        Ctrl+0
```

---

## 10. STATE MACHINE

```
                    ┌─────────────┐
                    │   STARTUP   │
                    └──────┬──────┘
                           ↓
                ┌──────────────────────┐
                │  WAITING_FOR_FOLDER  │ ← Prompt dialog
                │ (No PDFs loaded)     │
                └──────────┬───────────┘
                           ↓
                        [Select Folder]
                           ↓
                ┌──────────────────────┐
                │  FOLDER_SELECTED     │
                │ (PDFs loaded, ready) │
                └──────────┬───────────┘
                           ↓
        ┌──────────────────────────────────────┐
        │        VIEWING_PDF_STATE             │
        │                                      │
        │  ┌─────────────────────────────────┐ │
        │  │ Can perform:                    │ │
        │  │ • Zoom (in/out/reset)           │ │
        │  │ • Navigate pages (prev/next)    │ │
        │  │ • Select & copy text            │ │
        │  │ • [◀ Prev] to prev PDF          │ │
        │  │ • [Next ▶] to next PDF          │ │
        │  │ • [🔍 Analyze] → ANALYZING      │ │
        │  │ • [📁 Select] → WAITING_FOR...  │ │
        │  │ • [❌ Quit] → SHUTDOWN          │ │
        │  └─────────────────────────────────┘ │
        │                 ↕                    │
        │  ┌─────────────────────────────────┐ │
        │  │ ANALYZING_STATE                 │ │
        │  │                                 │ │
        │  │ • Progress bar visible          │ │
        │  │ • "Analyzing..." message        │ │
        │  │ • Buttons disabled              │ │
        │  │ • Extracts data → JSON editor   │ │
        │  │ • Returns to VIEWING_PDF        │ │
        │  └─────────────────────────────────┘ │
        │                                      │
        │  ┌─────────────────────────────────┐ │
        │  │ EDITING_JSON_STATE              │ │
        │  │                                 │ │
        │  │ • User edits JSON in editor     │ │
        │  │ • Real-time validation          │ │
        │  │ • Status indicator updates      │ │
        │  │ • [💾 Save & Next]:             │ │
        │  │   - Validates JSON              │ │
        │  │   - Saves to annotation file    │ │
        │  │   - Moves to next PDF           │ │
        │  │   - Auto-analyzes (if enabled) │ │
        │  └─────────────────────────────────┘ │
        │                                      │
        └──────────────────────────────────────┘
                    ↓        ↓
              [Quit]  [Last PDF]
                ↓        ↓
        ┌────────────────────────┐
        │      SHUTDOWN          │
        └────────────────────────┘
```

---

## 11. ERROR HANDLING & FEEDBACK

### Error Messages

```
Dialog Type     Message                        Action
─────────────────────────────────────────────────────────
Warning         "No Folder Selected"          → Select folder
Info            "No PDFs Found"               → Choose different folder
Warning         "Processing..."               → Wait for completion
Error           "Failed to load PDF: ..."     → Try another file
Error           "Failed to initialize..."     → Restart application
Info            "Saved to: ..."               → Confirm save location
```

### Progress Feedback

```
Visual Element        Indicates
──────────────────────────────────────────
Progress Bar          Active processing (indeterminate)
Progress Label        Current status message (updates in real-time)
Button States         Disabled during processing
Status Indicator      JSON validity (color-coded)
File Counter          Current position in batch
```

---

## 12. KNOWN FEATURES

### PDF Viewer Features
- ✓ Multi-page PDF support
- ✓ Page-by-page navigation
- ✓ Zoom controls (25-300%)
- ✓ Text selection with drag-to-select
- ✓ Copy text to clipboard
- ✓ Persistent zoom across navigation
- ✓ Visual selection rectangle

### JSON Editor Features
- ✓ Syntax highlighting
- ✓ Real-time JSON validation
- ✓ Status indicator (valid/invalid)
- ✓ Scrollable text area
- ✓ Editable fields for manual corrections
- ✓ Auto-population from extraction

### Application Features
- ✓ Folder picker dialog
- ✓ Recursive PDF discovery
- ✓ Auto-load existing annotations
- ✓ Background extraction processing
- ✓ Progress tracking with messages
- ✓ Auto-analyze option for batch processing
- ✓ Proper directory structure preservation
- ✓ Comprehensive error handling

---

## 13. PERFORMANCE & SYSTEM REQUIREMENTS

```
Requirement         Value
─────────────────────────────────────
Python Version      3.8+
Memory              ~500MB RAM (for PDF processing)
Display             Required (X11, Wayland, or Windows)
CPU                 Multi-threaded (extraction runs in background)

Performance:
• PDF Loading       <2 seconds
• Single PDF Analysis  5-7 seconds
• UI Responsiveness   No blocking during extraction
• Memory Efficiency   Reasonable for batch processing
```

---

## 14. SUMMARY

| Aspect | Details |
|--------|---------|
| **Window Size** | 1400×900px (resizable) |
| **Main Components** | Top bar, Split view (PDF+JSON), Bottom controls |
| **Color Theme** | Dark header, Light footer, Blue accents |
| **Input** | PDF files from user-selected folder |
| **Output** | JSON annotations in structured directory |
| **Processing** | Background threading, real-time progress |
| **User Actions** | Select folder, analyze, edit, save, navigate |
| **State** | Responsive, non-blocking UI during processing |

---

**Last Updated:** January 5, 2026  
**Status:** Current & Active  
**File:** `pdf_annotation_gui.py` (922 lines, fully functional)
