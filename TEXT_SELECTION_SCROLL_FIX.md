# Text Selection Scroll Fix

## Issue

User reported: "Something is wrong with the text selection box, when I scroll down the PDF view"

## Problem Analysis

### Symptom
When the PDF viewer is scrolled (vertically or horizontally), the text selection rectangle appears at the wrong position, not following the mouse cursor correctly.

### Root Cause

**Coordinate System Mismatch:**

Tkinter canvas uses two different coordinate systems:

1. **Window Coordinates** (what mouse events report)
   - Relative to the visible canvas area
   - Range: (0, 0) to (canvas_width, canvas_height)
   - Changes with window size, not scrolling

2. **Canvas Coordinates** (what canvas items use)
   - Absolute position on the full canvas
   - Range: (0, 0) to (scroll_region_width, scroll_region_height)
   - Fixed regardless of scrolling

**The Problem:**
```python
# Old code - WRONG when scrolled
def on_canvas_click(self, event):
    self.selection_start = (event.x, event.y)  # Window coordinates!
```

When scrolled, `event.x` and `event.y` don't match the actual position on the canvas.

### Example Scenario

```
PDF is 1000px tall
Canvas window shows 500px at a time
User scrolls down 300px

Mouse clicks at visible position: (100, 200)
├─ event.x = 100
└─ event.y = 200  ← Window coordinate

But actual canvas position: (100, 500)
├─ canvas.canvasx(event.x) = 100
└─ canvas.canvasy(event.y) = 500  ← Canvas coordinate (200 + 300 scroll)

Selection rectangle created at (100, 200) ← WRONG!
Should be created at (100, 500) ← CORRECT!
```

## Solution

### Code Changes

Convert all mouse event coordinates from window coordinates to canvas coordinates:

**1. On Click (Start Selection)**
```python
# Before
def on_canvas_click(self, event):
    self.selection_start = (event.x, event.y)

# After
def on_canvas_click(self, event):
    canvas_x = self.canvas.canvasx(event.x)
    canvas_y = self.canvas.canvasy(event.y)
    self.selection_start = (canvas_x, canvas_y)
```

**2. On Drag (Update Rectangle)**
```python
# Before
def on_canvas_drag(self, event):
    x1, y1 = event.x, event.y

# After
def on_canvas_drag(self, event):
    canvas_x = self.canvas.canvasx(event.x)
    canvas_y = self.canvas.canvasy(event.y)
    x1, y1 = canvas_x, canvas_y
```

**3. On Release (Finalize Selection)**
```python
# Before
def on_canvas_release(self, event):
    x1, y1 = event.x, event.y

# After
def on_canvas_release(self, event):
    canvas_x = self.canvas.canvasx(event.x)
    canvas_y = self.canvas.canvasy(event.y)
    x1, y1 = canvas_x, canvas_y
```

## How It Works

### Canvas Coordinate Conversion Methods

**`canvas.canvasx(x, gridspacing=None)`**
- Converts window X coordinate to canvas X coordinate
- Accounts for horizontal scrolling
- Returns absolute position on canvas

**`canvas.canvasy(y, gridspacing=None)`**
- Converts window Y coordinate to canvas Y coordinate
- Accounts for vertical scrolling
- Returns absolute position on canvas

### Visual Demonstration

#### Without Scrolling
```
┌─────────────────────────────────┐
│ Canvas Window (Visible Area)   │
│                                 │
│  Mouse at (100, 150)            │
│  ├─ event.x = 100              │
│  ├─ event.y = 150              │
│  ├─ canvasx(100) = 100         │
│  └─ canvasy(150) = 150         │
│                                 │
│  Selection box at (100, 150) ✓ │
└─────────────────────────────────┘
No scroll: Window coords = Canvas coords
```

#### With Scrolling (200px down)
```
┌─────────────────────────────────┐
│ Canvas Window (Visible Area)   │  Scroll: 200px down ↓
│                                 │
│  Mouse at (100, 150)            │
│  ├─ event.x = 100              │
│  ├─ event.y = 150              │  ← Window coordinate
│  ├─ canvasx(100) = 100         │
│  └─ canvasy(150) = 350         │  ← Canvas coordinate (150+200)
│                                 │
│  Selection box at (100, 350) ✓ │  ← Correct position!
└─────────────────────────────────┘
               ↑
         Hidden above
```

## Testing

### Test Cases

**Test 1: Selection Without Scrolling**
- Load PDF
- Don't scroll
- Select text
- ✅ Should work as before

**Test 2: Selection After Vertical Scroll**
- Load PDF
- Scroll down
- Select text
- ✅ Rectangle should appear at mouse cursor

**Test 3: Selection After Horizontal Scroll**
- Load PDF at high zoom (wider than window)
- Scroll right
- Select text
- ✅ Rectangle should appear at mouse cursor

**Test 4: Selection After Both Scrolls**
- Load PDF
- Scroll down and right
- Select text
- ✅ Rectangle should appear at mouse cursor

**Test 5: Selection While Dragging Across Scroll**
- Start selection
- Drag while canvas auto-scrolls
- Release
- ✅ Rectangle should cover dragged area

### Expected Behavior

1. **Click:** Selection starts at mouse position (visible)
2. **Drag:** Blue dashed rectangle follows mouse (visible)
3. **Release:** Green outline appears at correct text (visible)
4. **Copy:** Selected text matches visual selection (correct)

## Technical Details

### Coordinate Transformation Formula

```python
canvas_coordinate = window_coordinate + scroll_offset

# Implemented as:
canvas_x = canvas.canvasx(event.x)
canvas_y = canvas.canvasy(event.y)
```

### Scroll Region

The canvas scroll region is set when PDF is rendered:
```python
self.canvas.config(scrollregion=self.canvas.bbox("all"))
```

This defines the total scrollable area, which can be larger than the visible window.

### Mouse Event Coordinates

**Event Object Attributes:**
- `event.x` - Window X (0 to canvas width)
- `event.y` - Window Y (0 to canvas height)
- `event.x_root` - Screen X (absolute)
- `event.y_root` - Screen Y (absolute)

**Canvas Methods:**
- `canvas.canvasx(x)` - Window X → Canvas X
- `canvas.canvasy(y)` - Window Y → Canvas Y

## Comparison

### Before Fix (Broken with Scrolling)

```
User scrolls 300px down
Mouse clicks at window (100, 200)

Selection rectangle created at:
  (100, 200)  ← Wrong! Window coordinates used

Text at canvas position (100, 500) not selected
Rectangle appears 300px above cursor ✗
```

### After Fix (Works with Scrolling)

```
User scrolls 300px down
Mouse clicks at window (100, 200)

Selection rectangle created at:
  (100, 500)  ← Correct! Canvas coordinates used
  
Text at canvas position (100, 500) selected
Rectangle appears at cursor ✓
```

## Edge Cases

### Large PDFs
- **Issue:** Very large PDFs with extensive scrolling
- **Solution:** Coordinate conversion handles any scroll amount

### High Zoom
- **Issue:** Zoomed PDFs wider/taller than window
- **Solution:** Coordinate conversion independent of zoom level

### Rapid Scrolling
- **Issue:** User scrolls while selecting
- **Solution:** Each event converted independently

### Zero Scroll
- **Issue:** Coordinate conversion overhead when not scrolled
- **Solution:** Minimal overhead, functions return same value

## Summary

**Problem:** Text selection broken when PDF scrolled
**Cause:** Used window coordinates instead of canvas coordinates
**Solution:** Convert all event coordinates using `canvasx()` and `canvasy()`
**Result:** Selection works correctly at any scroll position

---

**Fix committed in:** 22c76f4
**Date:** 2024-12-18

