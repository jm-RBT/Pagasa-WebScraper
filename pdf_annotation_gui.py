#!/usr/bin/env python
"""
PDF Annotation GUI for PAGASA Typhoon Bulletins

A GUI tool for annotating PDFs with extracted JSON data from typhoon bulletins.
Uses TyphoonBulletinExtractor to automatically extract data and allows manual editing
before saving annotations.

Features:
- Split view: PDF viewer (left) and JSON editor (right)
- Automatic PDF discovery from dataset/pdfs/
- Automatic extraction using TyphoonBulletinExtractor
- Editable JSON with validation
- Navigation: Previous, Next, Save & Next
- Progress tracking
- Error handling and user feedback

Usage:
    python pdf_annotation_gui.py

Requirements:
    - Python 3.8+
    - tkinter (standard library)
    - pypdfium2 (for PDF rendering)
    - typhoon_extraction_ml.py (for extraction logic)
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import json
import threading
from pathlib import Path
from typing import List, Optional, Dict
import pypdfium2 as pdfium
from PIL import Image, ImageTk
import sys
import traceback
import pdfplumber

# Import the extraction logic
try:
    from typhoon_extraction_ml import TyphoonBulletinExtractor
except ImportError as e:
    print(f"Error: Cannot import TyphoonBulletinExtractor: {e}")
    print("Make sure typhoon_extraction_ml.py is in the same directory.")
    sys.exit(1)


class PDFViewer(tk.Frame):
    """PDF viewer widget using pypdfium2 for rendering"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.current_pdf = None
        self.current_pdf_path = None
        self.current_page = 0
        self.total_pages = 0
        self.zoom_level = 1.0  # Default zoom level
        
        # Text selection state
        self.text_chars = []  # List of character data with positions
        self.selected_text = ""
        self.selection_start = None
        self.selection_rect = None
        self.text_overlay_items = []  # Canvas items for text overlay
        
        # Create canvas for PDF display with scrollbar
        self.canvas_frame = tk.Frame(self)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.scrollbar_y = tk.Scrollbar(self.canvas_frame, orient=tk.VERTICAL)
        self.scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.scrollbar_x = tk.Scrollbar(self.canvas_frame, orient=tk.HORIZONTAL)
        self.scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.canvas = tk.Canvas(
            self.canvas_frame,
            bg='gray',
            xscrollcommand=self.scrollbar_x.set,
            yscrollcommand=self.scrollbar_y.set
        )
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.scrollbar_x.config(command=self.canvas.xview)
        self.scrollbar_y.config(command=self.canvas.yview)
        
        # Add text selection support
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<Control-c>", lambda e: self.copy_selected_text())
        
        # Page navigation and zoom controls
        nav_frame = tk.Frame(self)
        nav_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        
        self.page_label = tk.Label(nav_frame, text="Page 0 of 0")
        self.page_label.pack(side=tk.LEFT, padx=5)
        
        tk.Button(nav_frame, text="◀ Prev Page", command=self.prev_page).pack(side=tk.LEFT, padx=2)
        tk.Button(nav_frame, text="Next Page ▶", command=self.next_page).pack(side=tk.LEFT, padx=2)
        
        # Zoom controls
        tk.Label(nav_frame, text="|").pack(side=tk.LEFT, padx=5)
        tk.Button(nav_frame, text="🔍-", command=self.zoom_out, width=3).pack(side=tk.LEFT, padx=2)
        self.zoom_label = tk.Label(nav_frame, text="100%", width=5)
        self.zoom_label.pack(side=tk.LEFT, padx=2)
        tk.Button(nav_frame, text="🔍+", command=self.zoom_in, width=3).pack(side=tk.LEFT, padx=2)
        tk.Button(nav_frame, text="Reset", command=self.zoom_reset, width=5).pack(side=tk.LEFT, padx=2)
        
        # Copy selected text button
        tk.Label(nav_frame, text="|").pack(side=tk.LEFT, padx=5)
        tk.Button(nav_frame, text="📋 Copy Selected", command=self.copy_selected_text, width=12).pack(side=tk.LEFT, padx=2)
        tk.Label(nav_frame, text="(or Ctrl+C)", font=("Arial", 8), fg="gray").pack(side=tk.LEFT)
    
    def load_pdf(self, pdf_path: str, zoom_level: float = 1.0):
        """Load a PDF file and display the first page"""
        try:
            # Close previous PDF if any
            if self.current_pdf:
                self.current_pdf.close()
            
            # Open new PDF
            self.current_pdf = pdfium.PdfDocument(pdf_path)
            self.current_pdf_path = pdf_path
            self.total_pages = len(self.current_pdf)
            self.current_page = 0
            self.zoom_level = zoom_level  # Use provided zoom level
            
            self.render_page()
            
        except Exception as e:
            messagebox.showerror("PDF Load Error", f"Failed to load PDF:\n{e}")
            self.current_pdf = None
            self.current_pdf_path = None
            self.total_pages = 0
            self.current_page = 0
    
    def render_page(self):
        """Render the current page to canvas with text overlay"""
        if not self.current_pdf or self.total_pages == 0:
            self.canvas.delete("all")
            self.page_label.config(text="Page 0 of 0")
            self.zoom_label.config(text="100%")
            return
        
        try:
            # Get the page
            page = self.current_pdf[self.current_page]
            
            # Render at resolution based on zoom level (base scale 2 = 144 DPI)
            scale = 2 * self.zoom_level
            pil_image = page.render(scale=scale).to_pil()
            
            # Convert to PhotoImage
            self.photo = ImageTk.PhotoImage(pil_image)
            
            # Clear canvas and display
            self.canvas.delete("all")
            self.text_overlay_items = []
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
            
            # Extract text with coordinates for selection
            self.extract_text_with_coordinates()
            
            # Update scroll region
            self.canvas.config(scrollregion=self.canvas.bbox("all"))
            
            # Update labels
            self.page_label.config(text=f"Page {self.current_page + 1} of {self.total_pages}")
            self.zoom_label.config(text=f"{int(self.zoom_level * 100)}%")
            
        except Exception as e:
            messagebox.showerror("Render Error", f"Failed to render page:\n{e}")
    
    def extract_text_with_coordinates(self):
        """Extract text with character-level coordinates from PDF"""
        if not self.current_pdf_path:
            return
        
        try:
            with pdfplumber.open(self.current_pdf_path) as pdf:
                if self.current_page < len(pdf.pages):
                    page = pdf.pages[self.current_page]
                    
                    # Extract characters with their bounding boxes
                    chars = page.chars
                    
                    # Store character data scaled to match zoom level
                    self.text_chars = []
                    scale = 2 * self.zoom_level  # Match the render scale
                    
                    for char in chars:
                        char_data = {
                            'text': char['text'],
                            'x0': char['x0'] * scale,
                            'y0': char['top'] * scale,
                            'x1': char['x1'] * scale,
                            'y1': char['bottom'] * scale,
                            'width': (char['x1'] - char['x0']) * scale,
                            'height': (char['bottom'] - char['top']) * scale
                        }
                        self.text_chars.append(char_data)
        except Exception as e:
            # Silent fail - text selection won't work but PDF will still display
            self.text_chars = []
    
    def zoom_in(self):
        """Zoom in"""
        if self.zoom_level < 3.0:  # Max 300%
            self.zoom_level += 0.25
            self.render_page()
    
    def zoom_out(self):
        """Zoom out"""
        if self.zoom_level > 0.25:  # Min 25%
            self.zoom_level -= 0.25
            self.render_page()
    
    def zoom_reset(self):
        """Reset zoom to 100%"""
        self.zoom_level = 1.0
        self.render_page()
    
    def get_zoom_level(self):
        """Get current zoom level"""
        return self.zoom_level
    
    def on_canvas_click(self, event):
        """Handle mouse click on canvas - start text selection"""
        # Convert window coordinates to canvas coordinates (accounts for scrolling)
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        self.selection_start = (canvas_x, canvas_y)
        if self.selection_rect:
            self.canvas.delete(self.selection_rect)
        self.selection_rect = None
        self.selected_text = ""
    
    def on_canvas_drag(self, event):
        """Handle mouse drag on canvas - show selection rectangle"""
        if self.selection_start:
            # Convert window coordinates to canvas coordinates (accounts for scrolling)
            canvas_x = self.canvas.canvasx(event.x)
            canvas_y = self.canvas.canvasy(event.y)
            
            x0, y0 = self.selection_start
            x1, y1 = canvas_x, canvas_y
            
            # Ensure proper rectangle coordinates
            left = min(x0, x1)
            top = min(y0, y1)
            right = max(x0, x1)
            bottom = max(y0, y1)
            
            if self.selection_rect:
                self.canvas.delete(self.selection_rect)
            
            # Create selection rectangle with dashed outline for visibility
            # Use tag to ensure it stays on top
            self.selection_rect = self.canvas.create_rectangle(
                left, top, right, bottom,
                outline="blue", width=2, dash=(4, 4),
                tags="selection"
            )
            # Raise the selection rectangle to ensure it's visible above the image
            self.canvas.tag_raise("selection")
    
    def on_canvas_release(self, event):
        """Handle mouse release on canvas - select text in rectangle"""
        if self.selection_start and self.selection_rect:
            # Convert window coordinates to canvas coordinates (accounts for scrolling)
            canvas_x = self.canvas.canvasx(event.x)
            canvas_y = self.canvas.canvasy(event.y)
            
            x0, y0 = self.selection_start
            x1, y1 = canvas_x, canvas_y
            
            # Ensure proper rectangle coordinates
            sel_left = min(x0, x1)
            sel_top = min(y0, y1)
            sel_right = max(x0, x1)
            sel_bottom = max(y0, y1)
            
            # Find all characters within the selection rectangle
            selected_chars = []
            for char in self.text_chars:
                # Check if character intersects with selection rectangle
                char_left = char['x0']
                char_top = char['y0']
                char_right = char['x1']
                char_bottom = char['y1']
                
                # Check for intersection
                if not (char_right < sel_left or char_left > sel_right or
                        char_bottom < sel_top or char_top > sel_bottom):
                    selected_chars.append(char)
            
            # Sort characters by position (top to bottom, left to right)
            selected_chars.sort(key=lambda c: (c['y0'], c['x0']))
            
            # Build selected text
            self.selected_text = ''.join(c['text'] for c in selected_chars)
            
            # Show visual feedback if text was selected
            if self.selected_text:
                # Keep selection rectangle visible briefly
                self.canvas.itemconfig(self.selection_rect, outline="green", width=3)
                self.after(300, lambda: self._clear_selection_rect())
            else:
                self._clear_selection_rect()
        else:
            self._clear_selection_rect()
        
        self.selection_start = None
    
    def _clear_selection_rect(self):
        """Clear the selection rectangle"""
        if self.selection_rect:
            self.canvas.delete(self.selection_rect)
        self.selection_rect = None
    
    def copy_selected_text(self):
        """Copy the currently selected text to clipboard"""
        if self.selected_text:
            try:
                self.clipboard_clear()
                self.clipboard_append(self.selected_text)
                # Show brief message
                messagebox.showinfo("Text Copied", 
                    f"Copied {len(self.selected_text)} characters:\n\n{self.selected_text[:100]}{'...' if len(self.selected_text) > 100 else ''}")
            except Exception as e:
                messagebox.showerror("Copy Error", f"Failed to copy text:\n{e}")
        else:
            messagebox.showinfo("No Selection", "No text selected. Drag to select text first.")
    
    
    def next_page(self):
        """Go to next page"""
        if self.current_pdf and self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.render_page()
    
    def prev_page(self):
        """Go to previous page"""
        if self.current_pdf and self.current_page > 0:
            self.current_page -= 1
            self.render_page()
    
    def close(self):
        """Clean up resources"""
        if self.current_pdf:
            self.current_pdf.close()
            self.current_pdf = None
            self.current_pdf_path = None


class JSONEditor(tk.Frame):
    """JSON editor widget with syntax validation"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        # Title
        title_label = tk.Label(self, text="Extracted JSON (Editable)", font=("Arial", 10, "bold"))
        title_label.pack(side=tk.TOP, pady=(5, 2))
        
        # Text widget with scrollbar
        self.text_widget = scrolledtext.ScrolledText(
            self,
            wrap=tk.NONE,
            font=("Courier", 9),
            undo=True,
            maxundo=-1
        )
        self.text_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Status label
        self.status_label = tk.Label(self, text="", fg="green")
        self.status_label.pack(side=tk.BOTTOM, pady=2)
    
    def set_json(self, data: Dict):
        """Set JSON data in the editor"""
        try:
            json_str = json.dumps(data, indent=2, ensure_ascii=False)
            self.text_widget.delete(1.0, tk.END)
            self.text_widget.insert(1.0, json_str)
            self.status_label.config(text="✓ Valid JSON", fg="green")
        except Exception as e:
            self.status_label.config(text=f"✗ Error: {e}", fg="red")
    
    def get_json(self) -> Optional[Dict]:
        """Get JSON data from editor with validation"""
        try:
            json_str = self.text_widget.get(1.0, tk.END).strip()
            if not json_str:
                return None
            data = json.loads(json_str)
            self.status_label.config(text="✓ Valid JSON", fg="green")
            return data
        except json.JSONDecodeError as e:
            self.status_label.config(text=f"✗ Invalid JSON: {e}", fg="red")
            return None
        except Exception as e:
            self.status_label.config(text=f"✗ Error: {e}", fg="red")
            return None
    
    def clear(self):
        """Clear the editor"""
        self.text_widget.delete(1.0, tk.END)
        self.status_label.config(text="", fg="black")


class PDFAnnotationApp:
    """Main application window"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("PAGASA PDF Annotation Tool")
        self.root.geometry("1400x900")
        
        # State
        self.pdf_files: List[Path] = []
        self.current_index = 0
        self.extractor = None
        self.is_processing = False
        self.pdf_folder = None
        self.saved_zoom_level = 1.0  # Remember zoom level across PDFs
        self.auto_analyze_next = tk.BooleanVar(value=False)  # Auto-analyze checkbox state
        
        # Setup UI
        self.setup_ui()
        
        # Initialize extractor in background
        self.init_extractor()
        
        # Don't auto-load PDFs - wait for user to select folder
        self.prompt_folder_selection()
    
    def setup_ui(self):
        """Create the user interface"""
        
        # Top bar with title and file counter
        top_frame = tk.Frame(self.root, bg="#2c3e50", height=40)
        top_frame.pack(side=tk.TOP, fill=tk.X)
        top_frame.pack_propagate(False)
        
        title_label = tk.Label(
            top_frame,
            text="📄 PAGASA PDF Annotation Tool",
            font=("Arial", 14, "bold"),
            fg="white",
            bg="#2c3e50"
        )
        title_label.pack(side=tk.LEFT, padx=20, pady=5)
        
        self.file_counter_label = tk.Label(
            top_frame,
            text="File 0 of 0",
            font=("Arial", 12),
            fg="white",
            bg="#2c3e50"
        )
        self.file_counter_label.pack(side=tk.RIGHT, padx=20, pady=5)
        
        # Main content area with split view
        content_frame = tk.Frame(self.root)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Use PanedWindow for resizable split view
        paned_window = tk.PanedWindow(content_frame, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        paned_window.pack(fill=tk.BOTH, expand=True)
        
        # Left panel: PDF viewer
        left_frame = tk.Frame(paned_window, relief=tk.SUNKEN, borderwidth=1)
        self.pdf_viewer = PDFViewer(left_frame)
        self.pdf_viewer.pack(fill=tk.BOTH, expand=True)
        paned_window.add(left_frame, minsize=400)
        
        # Right panel: JSON editor
        right_frame = tk.Frame(paned_window, relief=tk.SUNKEN, borderwidth=1)
        self.json_editor = JSONEditor(right_frame)
        self.json_editor.pack(fill=tk.BOTH, expand=True)
        paned_window.add(right_frame, minsize=400)
        
        # Bottom bar with navigation buttons
        bottom_frame = tk.Frame(self.root, bg="#ecf0f1", height=110)  # Increased from 60 to 80
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)
        bottom_frame.pack_propagate(False)
        
        # Progress bar
        self.progress_label = tk.Label(
            bottom_frame,
            text="Ready - Please select a folder",
            font=("Arial", 9),
            bg="#ecf0f1"
        )
        self.progress_label.pack(side=tk.TOP, pady=(5, 0))
        
        self.progress_bar = ttk.Progressbar(
            bottom_frame,
            mode='indeterminate',
            length=200
        )
        
        # Auto-analyze checkbox
        checkbox_frame = tk.Frame(bottom_frame, bg="#ecf0f1")
        checkbox_frame.pack(side=tk.TOP, pady=(2, 5))
        
        self.auto_analyze_checkbox = tk.Checkbutton(
            checkbox_frame,
            text="Auto-analyze next PDF after Save & Next",
            variable=self.auto_analyze_next,
            font=("Arial", 9),
            bg="#ecf0f1"
        )
        self.auto_analyze_checkbox.pack()
        
        # Navigation buttons
        button_frame = tk.Frame(bottom_frame, bg="#ecf0f1")
        button_frame.pack(side=tk.BOTTOM, pady=10)
        
        tk.Button(
            button_frame,
            text="📁 Select Folder",
            command=self.select_folder,
            width=13,
            height=2,  # Added height
            font=("Arial", 10),
            bg="#95a5a6",
            fg="white"
        ).pack(side=tk.LEFT, padx=5)
        
        self.prev_button = tk.Button(
            button_frame,
            text="◀ Previous",
            command=self.prev_file,
            width=12,
            height=2,  # Added height
            font=("Arial", 10)
        )
        self.prev_button.pack(side=tk.LEFT, padx=5)
        
        self.analyze_button = tk.Button(
            button_frame,
            text="🔍 Analyze",
            command=self.analyze_current,
            width=12,
            height=2,  # Added height
            font=("Arial", 10, "bold"),
            bg="#e67e22",
            fg="white"
        )
        self.analyze_button.pack(side=tk.LEFT, padx=5)
        
        self.save_next_button = tk.Button(
            button_frame,
            text="💾 Save & Next",
            command=self.save_and_next,
            width=15,
            height=2,  # Added height
            font=("Arial", 10, "bold"),
            bg="#3498db",
            fg="white"
        )
        self.save_next_button.pack(side=tk.LEFT, padx=5)
        
        self.next_button = tk.Button(
            button_frame,
            text="Next ▶",
            command=self.next_file,
            width=12,
            height=2,  # Added height
            font=("Arial", 10)
        )
        self.next_button.pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            button_frame,
            text="❌ Quit",
            command=self.quit_app,
            width=10,
            height=2,  # Added height
            font=("Arial", 10)
        ).pack(side=tk.LEFT, padx=20)
    
    def prompt_folder_selection(self):
        """Prompt user to select PDF folder on startup"""
        self.root.after(500, self._show_folder_dialog)
    
    def _show_folder_dialog(self):
        """Show folder selection dialog"""
        result = messagebox.askyesno(
            "Select PDF Folder",
            "Would you like to select a folder containing PDFs to annotate?"
        )
        if result:
            self.select_folder()
    
    def select_folder(self):
        """Let user select folder containing PDFs"""
        folder = filedialog.askdirectory(
            title="Select Folder with PDFs",
            initialdir=Path.cwd() / "dataset" / "pdfs" if (Path.cwd() / "dataset" / "pdfs").exists() else Path.cwd()
        )
        
        if folder:
            self.pdf_folder = Path(folder)
            self.load_pdf_list()
    
    def init_extractor(self):
        """Initialize the TyphoonBulletinExtractor in background"""
        def init_task():
            try:
                self.update_progress("Initializing extractor...")
                self.extractor = TyphoonBulletinExtractor()
                self.update_progress("Extractor ready", hide_after=2)
            except Exception as e:
                self.update_progress(f"Extractor init failed: {e}", hide_after=5)
                messagebox.showerror("Initialization Error", 
                                   f"Failed to initialize extractor:\n{e}\n\nSome features may not work.")
        
        threading.Thread(target=init_task, daemon=True).start()
    
    def load_pdf_list(self):
        """Find all PDFs in selected folder"""
        if not self.pdf_folder:
            messagebox.showwarning(
                "No Folder Selected",
                "Please select a folder containing PDFs first."
            )
            return
        
        try:
            if not self.pdf_folder.exists():
                messagebox.showwarning(
                    "Directory Not Found",
                    f"PDF directory not found: {self.pdf_folder}"
                )
                return
            
            # Find all PDFs recursively
            self.pdf_files = sorted(list(self.pdf_folder.rglob("*.pdf")))
            
            if not self.pdf_files:
                messagebox.showinfo(
                    "No PDFs Found",
                    f"No PDF files found in {self.pdf_folder}\n\nPlease select a different folder."
                )
                return
            
            # Load first PDF (but don't analyze it)
            self.current_index = 0
            self.load_current_pdf()
            self.update_progress(f"Loaded {len(self.pdf_files)} PDFs from folder", hide_after=3)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load PDF list:\n{e}")
    
    def load_current_pdf(self):
        """Load the current PDF (without analyzing)"""
        if not self.pdf_files:
            return
        
        if self.is_processing:
            messagebox.showinfo("Processing", "Please wait for current operation to complete.")
            return
        
        try:
            # Save current zoom level before loading new PDF
            if hasattr(self, 'pdf_viewer') and hasattr(self.pdf_viewer, 'get_zoom_level'):
                self.saved_zoom_level = self.pdf_viewer.get_zoom_level()
            
            current_file = self.pdf_files[self.current_index]
            
            # Update UI
            self.update_file_counter()
            # Load PDF with saved zoom level
            self.pdf_viewer.load_pdf(str(current_file), self.saved_zoom_level)
            
            # Check if annotation already exists
            annotation_path = self.get_annotation_path(current_file)
            if annotation_path.exists():
                # Load existing annotation
                with open(annotation_path, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                self.json_editor.set_json(existing_data)
                self.update_progress(f"Loaded existing annotation", hide_after=3)
            else:
                # Clear JSON editor - wait for user to click Analyze
                self.json_editor.clear()
                self.update_progress("PDF loaded - Click 'Analyze' to extract data", hide_after=5)
        
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load PDF:\n{e}\n\n{traceback.format_exc()}")
    
    def analyze_current(self):
        """Analyze the current PDF (manual trigger)"""
        if not self.pdf_files:
            messagebox.showinfo("No PDF", "No PDF loaded. Please select a folder first.")
            return
        
        if self.is_processing:
            messagebox.showinfo("Processing", "Please wait for current operation to complete.")
            return
        
        current_file = self.pdf_files[self.current_index]
        self.json_editor.clear()
        self.analyze_pdf_async(current_file)
    
    def analyze_pdf_async(self, pdf_path: Path):
        """Analyze PDF in background thread"""
        if not self.extractor:
            self.json_editor.set_json({"error": "Extractor not initialized"})
            return
        
        def analyze_task():
            try:
                self.is_processing = True
                self.update_progress(f"Analyzing {pdf_path.name}...")
                self.toggle_buttons(False)
                
                # Extract data
                data = self.extractor.extract_from_pdf(str(pdf_path))
                
                # Update UI in main thread
                self.root.after(0, lambda: self.on_analysis_complete(data))
                
            except Exception as e:
                error_data = {
                    "error": f"Extraction failed: {e}",
                    "traceback": traceback.format_exc()
                }
                self.root.after(0, lambda: self.on_analysis_complete(error_data))
            finally:
                self.is_processing = False
                self.root.after(0, lambda: self.toggle_buttons(True))
        
        threading.Thread(target=analyze_task, daemon=True).start()
    
    def on_analysis_complete(self, data: Dict):
        """Handle completed analysis"""
        if data:
            self.json_editor.set_json(data)
            if "error" in data:
                self.update_progress(f"Extraction failed", hide_after=5)
            else:
                self.update_progress(f"Extraction complete", hide_after=3)
        else:
            self.json_editor.set_json({"error": "No data extracted"})
            self.update_progress(f"No data extracted", hide_after=5)
    
    
    def get_annotation_path(self, pdf_path: Path) -> Path:
        """Get the annotation file path for a PDF"""
        # Get relative path from the selected folder
        if self.pdf_folder:
            try:
                relative_path = pdf_path.relative_to(self.pdf_folder)
            except ValueError:
                # If pdf_path is not relative to pdf_folder, use just the filename
                relative_path = Path(pdf_path.name)
        else:
            relative_path = Path(pdf_path.name)
        
        # Create annotation path in dataset/pdfs_annotation/
        annotation_dir = Path("dataset/pdfs_annotation") / relative_path.parent
        annotation_path = annotation_dir / f"{pdf_path.stem}.json"
        
        return annotation_path
    
    def save_current_annotation(self) -> bool:
        """Save the current annotation"""
        if not self.pdf_files:
            return False
        
        try:
            # Get and validate JSON
            json_data = self.json_editor.get_json()
            if json_data is None:
                messagebox.showerror("Invalid JSON", "Cannot save invalid JSON. Please fix errors first.")
                return False
            
            # Get annotation path
            current_file = self.pdf_files[self.current_index]
            annotation_path = self.get_annotation_path(current_file)
            
            # Create directory if needed
            annotation_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save JSON
            with open(annotation_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            
            self.update_progress(f"Saved: {annotation_path.name}", hide_after=3)
            return True
            
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save annotation:\n{e}")
            return False
    
    def prev_file(self):
        """Go to previous PDF"""
        if not self.pdf_files:
            return
        
        if self.is_processing:
            messagebox.showinfo("Processing", "Please wait for current operation to complete.")
            return
        
        if self.current_index > 0:
            self.current_index -= 1
            self.load_current_pdf()
        else:
            messagebox.showinfo("First File", "Already at the first file.")
    
    def next_file(self):
        """Go to next PDF"""
        if not self.pdf_files:
            return
        
        if self.is_processing:
            messagebox.showinfo("Processing", "Please wait for current operation to complete.")
            return
        
        if self.current_index < len(self.pdf_files) - 1:
            self.current_index += 1
            self.load_current_pdf()
        else:
            messagebox.showinfo("Last File", "Already at the last file.")
    
    def save_and_next(self):
        """Save current annotation and move to next"""
        if not self.pdf_files:
            return
        
        if self.is_processing:
            messagebox.showinfo("Processing", "Please wait for current operation to complete.")
            return
        
        # Save current
        if self.save_current_annotation():
            # Move to next
            if self.current_index < len(self.pdf_files) - 1:
                self.current_index += 1
                self.load_current_pdf()
                
                # Auto-analyze if checkbox is checked
                if self.auto_analyze_next.get():
                    # Schedule analysis after a short delay to let UI update
                    self.root.after(100, self.analyze_current)
            else:
                messagebox.showinfo("Complete", "All files processed!")
    
    def update_file_counter(self):
        """Update the file counter label"""
        if self.pdf_files:
            current_file = self.pdf_files[self.current_index]
            text = f"File {self.current_index + 1} of {len(self.pdf_files)}: {current_file.name}"
        else:
            text = "No files loaded"
        
        self.file_counter_label.config(text=text)
    
    def update_progress(self, message: str, hide_after: int = 0):
        """Update progress message"""
        self.progress_label.config(text=message)
        
        if hide_after > 0:
            self.root.after(hide_after * 1000, lambda: self.progress_label.config(text="Ready"))
    
    def toggle_buttons(self, enabled: bool):
        """Enable/disable navigation buttons"""
        state = tk.NORMAL if enabled else tk.DISABLED
        self.prev_button.config(state=state)
        self.next_button.config(state=state)
        self.save_next_button.config(state=state)
        
        # Show/hide progress bar
        if enabled:
            self.progress_bar.pack_forget()
            self.progress_bar.stop()
        else:
            self.progress_bar.pack(side=tk.TOP, pady=2)
            self.progress_bar.start(10)
    
    def quit_app(self):
        """Quit the application"""
        if self.is_processing:
            messagebox.showinfo("Processing", "Please wait for current operation to complete.")
            return
        
        if messagebox.askyesno("Quit", "Are you sure you want to quit?"):
            # Clean up
            self.pdf_viewer.close()
            self.root.quit()
            self.root.destroy()


def main():
    """Main entry point"""
    try:
        # Create root window
        root = tk.Tk()
        
        # Create app
        app = PDFAnnotationApp(root)
        
        # Run
        root.mainloop()
        
    except Exception as e:
        print(f"Fatal error: {e}")
        traceback.print_exc()
        messagebox.showerror("Fatal Error", f"Application crashed:\n{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
