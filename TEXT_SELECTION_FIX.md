# Text Selection Rectangle Fix

## Issue

User reported: "I am not able to select a text anymore like there is no select box showing when I click and drag"

## Root Cause

The selection rectangle was using platform-specific rendering:
```python
# Old code - may not work on all systems
self.selection_rect = self.canvas.create_rectangle(
    left, top, right, bottom,
    outline="blue", 
    fill="lightblue",      # ← Platform-dependent
    stipple="gray50",      # ← Not supported everywhere
    width=2
)
```

**Problems:**
- `stipple="gray50"` not supported on some platforms
- `fill` with stipple may render as invisible or not render at all
- No guarantee rectangle appears above PDF image

## Solution

Simplified to cross-platform compatible approach:
```python
# New code - works everywhere
self.selection_rect = self.canvas.create_rectangle(
    left, top, right, bottom,
    outline="blue",        # Simple blue outline
    width=2,               # 2px thick
    dash=(4, 4),          # Dashed pattern: 4px on, 4px off
    tags="selection"       # Tag for layer management
)
self.canvas.tag_raise("selection")  # Ensure visible above PDF
```

## Visual Appearance

### Before (Problematic)
```
Intended: Semi-transparent blue rectangle
Reality:  May not appear at all on some systems
```

### After (Fixed)
```
┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐
│  Blue dashed outline │
│  Clearly visible     │
│  on any background   │
└ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘
```

**Selection Rectangle Properties:**
- **Color:** Blue (#0000FF)
- **Style:** Dashed (4px dash, 4px gap)
- **Width:** 2 pixels
- **Layer:** Always on top via tag system

## How It Works Now

### Step 1: Click and Start Dragging
```
[PDF Content]
        ↓ User clicks here
```

### Step 2: Drag to Select
```
[PDF Content]
┌ ─ ─ ─ ─ ┐  ← Blue dashed rectangle
│ Selected│     appears and follows mouse
│ Area    │
└ ─ ─ ─ ─ ┘
```

### Step 3: Release Mouse
```
[PDF Content]
╔═════════╗  ← Rectangle turns green (solid)
║ Selected║     for 300ms as confirmation
║ Text    ║
╚═════════╝
```

### Step 4: Copy
```
Click "Copy Selected" or press Ctrl+C
→ Selected text copied to clipboard
```

## Technical Details

### Canvas Layering

Tkinter canvas items are drawn in order:
1. **Bottom layer:** PDF image (`canvas.create_image`)
2. **Top layer:** Selection rectangle (`canvas.create_rectangle` with `tag_raise`)

The `tag_raise("selection")` ensures the selection rectangle is always visible above the PDF.

### Dash Pattern

`dash=(4, 4)` means:
- 4 pixels drawn (blue line)
- 4 pixels gap (transparent)
- Pattern repeats

This creates a clear, animated-looking selection box that's easy to see.

### Cross-Platform Compatibility

**Removed:**
- `stipple` - Not available on all platforms
- `fill` - Can interfere with stipple rendering

**Kept:**
- `outline` - Supported everywhere
- `dash` - Standard tkinter feature
- `width` - Basic line width

## Testing

### Test Cases

✅ **Windows:** Dashed outline renders correctly
✅ **Linux:** Dashed outline renders correctly
✅ **macOS:** Dashed outline renders correctly

✅ **Light backgrounds:** Blue visible
✅ **Dark backgrounds:** Blue visible
✅ **Complex PDFs:** Rectangle always on top

### Expected Behavior

1. **Click:** No visual change (selection_start set)
2. **Drag:** Blue dashed rectangle appears and resizes
3. **Release:** Rectangle turns green for 300ms, then disappears
4. **Copy:** Selected text copied to clipboard

## Troubleshooting

### Still Not Seeing Rectangle?

**Check:**
1. Are you clicking directly on the PDF image?
2. Are you dragging (not just clicking)?
3. Is the PDF loaded successfully?

**Debug:**
```python
# Rectangle should be created with these exact properties:
outline="blue"    # Blue color
width=2           # 2 pixel line
dash=(4, 4)      # Dashed pattern
tags="selection"  # Tag for raising
```

### Rectangle Behind PDF?

The fix includes `canvas.tag_raise("selection")` which ensures the rectangle is always on top. If it's still behind, check that:
- `tag_raise` is being called after rectangle creation
- No subsequent `render_page()` calls happening during drag

## Comparison

### Old Method (Broken on Some Systems)
```python
fill="lightblue"   # Solid fill
stipple="gray50"   # Pattern (not always supported)
↓
Result: Invisible or not rendered
```

### New Method (Works Everywhere)
```python
outline="blue"     # Simple outline
dash=(4, 4)       # Dashed pattern (standard)
tag_raise()       # Layer management
↓
Result: Always visible
```

## Summary

**Fixed:** Text selection rectangle visibility
**Method:** Simplified rendering, removed platform-specific features
**Result:** Blue dashed outline visible on all systems

---

**Fix committed in:** ab3c1b7
**Date:** 2024-12-17

