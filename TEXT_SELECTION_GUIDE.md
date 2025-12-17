# Selective Text Selection Feature - User Guide

## Overview

The PDF viewer now supports **selective text selection** - you can drag to select any specific text in the PDF and copy only what you selected.

## How It Works

### 1. Visual Selection
```
┌─────────────────────────────────────────┐
│  SEVERE WEATHER BULLETIN                │
│  ──────────────────────                 │
│                                         │
│  Tropical Cyclone PEPITO                │
│  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓        │
│  ┃ Location: 60 km NE of...  ┃ ← Blue  │
│  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛        │
│  Wind Speed: 150 km/h                   │
│                                         │
└─────────────────────────────────────────┘
```

When you drag your mouse, a **blue semi-transparent rectangle** appears showing your selection area.

### 2. Selection Complete
```
┌─────────────────────────────────────────┐
│  SEVERE WEATHER BULLETIN                │
│  ──────────────────────                 │
│                                         │
│  Tropical Cyclone PEPITO                │
│  ╔═══════════════════════════════╗      │
│  ║ Location: 60 km NE of...  ║ ← Green │
│  ╚═══════════════════════════════╝      │
│  Wind Speed: 150 km/h                   │
│                                         │
└─────────────────────────────────────────┘
```

When you release the mouse, the rectangle briefly turns **green** to confirm text was selected.

### 3. Copy Text
```
Click: [📋 Copy Selected]  or  Press: Ctrl+C
         ↓
┌────────────────────────────────┐
│ ✓ Text Copied                  │
│                                │
│ Copied 24 characters:          │
│                                │
│ Location: 60 km NE of...       │
└────────────────────────────────┘
```

## Step-by-Step Usage

### Basic Selection
1. **Load a PDF** in the viewer
2. **Click and drag** over the text you want to select
3. **Release** the mouse button
4. **Click** "Copy Selected" button or **press Ctrl+C**
5. Text is now in your clipboard!

### Tips for Better Selection

**Selecting a Single Word:**
- Click at the start of the word
- Drag to the end of the word
- Release

**Selecting Multiple Lines:**
- Click at the start of the first line
- Drag down and across to the end of the last line
- Release

**Selecting a Paragraph:**
- Click at the top-left of the paragraph
- Drag to the bottom-right
- Release

**Selecting Specific Numbers/Data:**
- Zoom in for better precision (use 🔍+ button)
- Select the exact area needed
- Copy

## Technical Details

### How Selection Works

1. **Character Extraction:**
   - PDF text extracted with character-level coordinates
   - Each character has position (x, y, width, height)

2. **Coordinate Scaling:**
   - Coordinates scaled to match current zoom level
   - Selection accurate at any zoom (25%-300%)

3. **Rectangle Selection:**
   - Mouse drag creates selection rectangle
   - All characters within rectangle are selected

4. **Text Building:**
   - Selected characters sorted by position
   - Text built left-to-right, top-to-bottom
   - Natural reading order preserved

### Selection Algorithm
```python
# Pseudocode
for each character in PDF:
    if character overlaps selection rectangle:
        add to selected_chars
        
sort selected_chars by (y_position, x_position)
selected_text = join(selected_chars)
```

## Visual Feedback

### Selection States

| State | Visual | Description |
|-------|--------|-------------|
| **Dragging** | Blue dashed outline | Active selection in progress |
| **Selected** | Green solid outline | Text selected, ready to copy |
| **Copied** | Message dialog | Confirmation with preview |

## Keyboard Shortcuts

- **Ctrl+C** - Copy selected text (after selection)
- **Click & Drag** - Select text area
- **Click without drag** - Clear selection

## Examples

### Example 1: Selecting Location
```
Before: "Tropical Cyclone PEPITO"
        "Location: 60 km NE of Manila"
        "Wind Speed: 150 km/h"

Select: Drag over "60 km NE of Manila"
Copy:   "60 km NE of Manila"
```

### Example 2: Selecting Multiple Fields
```
Before: "Wind Speed: 150 km/h"
        "Movement: WNW at 20 km/h"

Select: Drag over both lines
Copy:   "Wind Speed: 150 km/h Movement: WNW at 20 km/h"
```

### Example 3: Selecting Specific Numbers
```
Before: "Signal #1: Metro Manila, Cavite, Laguna"

Select: Drag over "Metro Manila, Cavite, Laguna"
Copy:   "Metro Manila, Cavite, Laguna"
```

## Troubleshooting

### No Text Selected
- **Symptom:** Message says "No text selected"
- **Cause:** Dragged over empty area or image
- **Solution:** Make sure to drag over actual text

### Wrong Text Selected
- **Symptom:** Selected text doesn't match visual selection
- **Cause:** PDF may have unusual text layout
- **Solution:** Try selecting smaller regions, zoom in for precision

### Can't Select Text
- **Symptom:** Selection doesn't work at all
- **Cause:** PDF may be image-based (scanned document)
- **Solution:** OCR would be needed for scanned PDFs

### Selection Rectangle Not Visible
- **Symptom:** No rectangle appears when dragging
- **Cause:** Mouse events not working
- **Solution:** Click directly on PDF image, not margin

## Comparison: Old vs New

### Old Behavior (Full Page Copy)
```
[📋 Copy Text] → Copies ALL text on page
                 No selection control
                 All or nothing
```

### New Behavior (Selective Copy)
```
1. Drag to select specific area
2. [📋 Copy Selected] → Copies ONLY selected text
                        Full control
                        Precise selection
```

## Benefits

✅ **Precision:** Select exactly what you need  
✅ **Flexibility:** Any text, any size, any location  
✅ **Efficiency:** No manual editing of copied text  
✅ **Visual:** See what you're selecting in real-time  
✅ **Intuitive:** Standard drag-to-select interface  

## System Requirements

- **PDF Type:** Text-based PDFs (not scanned images)
- **Dependencies:** pdfplumber (already installed)
- **OS:** Windows, Linux, macOS (cross-platform)
- **Input:** Mouse or trackpad with click-and-drag

## Future Enhancements

Possible improvements:
- Text highlighting (not just rectangle)
- Multi-select (Ctrl+Click for multiple regions)
- Word-boundary snapping
- Copy with formatting preserved
- Search and select

---

**Feature implemented in commit 9c32453**

