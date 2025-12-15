import logging
import json
from typing import List, Dict, Any, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MLTableParser:
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.model = None
        self.feature_extractor = None
        self.device = None
        self.id2label = None

    def _lazy_load_deps(self):
        """
        Lazily imports heavy dependencies (torch, transformers) and loads the model.
        This ensures zero performance impact when the ML parser is not used.
        """
        if self.model is not None:
            return

        logger.info("Loading ML dependencies (Torch, Transformers)...")
        
        try:
            import torch
            from transformers import TableTransformerForObjectDetection, DetrImageProcessor
            
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Using device: {self.device}")

            # Model: Microsoft Table Transformer (Structure Recognition)
            model_name = "microsoft/table-transformer-structure-recognition"
            
            self.feature_extractor = DetrImageProcessor.from_pretrained(model_name)
            self.model = TableTransformerForObjectDetection.from_pretrained(model_name)
            self.model.to(self.device)
            self.id2label = self.model.config.id2label
            self.torch = torch # Store reference to torch module
            
            logger.info("ML Model loaded successfully.")
            
        except ImportError as e:
            logger.error(f"Failed to load ML dependencies: {e}")
            raise ImportError("Please install 'torch', 'transformers', 'pillow', 'timm' to use MLTableParser.")

    def detect_tables(self, image) -> List[Dict]:
        """
        Detects table structure (rows, columns, headers) from an image.
        """
        self._lazy_load_deps()
        
        # Prepare image
        inputs = self.feature_extractor(images=image, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # Inference
        with self.torch.no_grad():
            outputs = self.model(**inputs)
            
        # Post-process (convert logits to boxes)
        target_sizes = self.torch.tensor([image.size[::-1]]).to(self.device)
        results = self.feature_extractor.post_process_object_detection(outputs, threshold=0.6, target_sizes=target_sizes)[0]
        
        detected_objects = []
        for score, label, box in zip(results["scores"], results["labels"], results["boxes"]):
            box = [round(i, 2) for i in box.tolist()]
            label_name = self.id2label[label.item()]
            detected_objects.append({
                "label": label_name,
                "score": round(score.item(), 4),
                "box": box  # [xmin, ymin, xmax, ymax]
            })
            
        return detected_objects

    def _get_iou(self, boxA, boxB):
        # Determine the (x, y)-coordinates of the intersection rectangle
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])

        # Compute the area of intersection rectangle
        interArea = max(0, xB - xA) * max(0, yB - yA)

        # Compute the area of both the prediction and ground-truth rectangles
        boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
        boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])

        # Compute the intersection over union by taking the intersection
        # area and dividing it by the sum of prediction + ground-truth
        # areas - the interesection area
        iou = interArea / float(boxAArea + boxBArea - interArea)

        return iou
        
    def _is_contained(self, inner_box, outer_box):
         # Check if inner_box is mostly inside outer_box
         # Relaxed containment: center point of inner is inside outer
         cx = (inner_box[0] + inner_box[2]) / 2
         cy = (inner_box[1] + inner_box[3]) / 2
         
         return (outer_box[0] <= cx <= outer_box[2] and 
                 outer_box[1] <= cy <= outer_box[3])

    def parse_page(self, pdf_page_image, words: List[Dict]) -> List[List[str]]:
        """
        Main logic:
        1. Detect Rows and Columns features
        2. Reconstruct Grid
        3. Assign Words to Cells
        """
        objects = self.detect_tables(pdf_page_image)
        
        rows = [obj for obj in objects if obj['label'] == 'table row']
        cols = [obj for obj in objects if obj['label'] == 'table column']
        
        # Robust Sorting
        # Rows: Sorted by Center-Y
        rows.sort(key=lambda x: (x['box'][1] + x['box'][3])/2)
        
        # Cols: Sorted by Center-X
        cols.sort(key=lambda x: (x['box'][0] + x['box'][2])/2)
        
        if not rows:
            logger.warning("No table rows detected. Returning raw text lines fallback.")
            # Fallback: Just bunch words by Y lines? 
            # For now return empty, pipeline will handle fallout
            return []
            
        # Grid Matrix
        grid = [['' for _ in range(len(cols))] for _ in range(len(rows))]
        
        # Word Assignment
        for word in words:
            # Word Box: [x0, top, x1, bottom]
            w_box = [word['x0'], word['top'], word['x1'], word['bottom']]
            
            # Find which cell this word belongs to
            # We check intersection with every cell
            best_iou = 0.0
            best_r, best_c = -1, -1
            
            for r_idx, row in enumerate(rows):
                for c_idx, col in enumerate(cols):
                    # Define Cell Box
                    r_box = row['box']
                    c_box = col['box']
                    
                    cell_box = [
                        max(r_box[0], c_box[0]),
                        max(r_box[1], c_box[1]),
                        min(r_box[2], c_box[2]),
                        min(r_box[3], c_box[3])
                    ]
                    
                    # Calculate overlapping area
                    # Intersection of Word and Cell
                    ix1 = max(w_box[0], cell_box[0])
                    iy1 = max(w_box[1], cell_box[1])
                    ix2 = min(w_box[2], cell_box[2])
                    iy2 = min(w_box[3], cell_box[3])
                    
                    if ix2 > ix1 and iy2 > iy1:
                        inter_area = (ix2 - ix1) * (iy2 - iy1)
                        word_area = (w_box[2] - w_box[0]) * (w_box[3] - w_box[1])
                        
                        # Overlap Ratio (how much of the word is inside the cell)
                        ratio = inter_area / word_area
                        
                        if ratio > 0.5 and ratio > best_iou:
                            best_iou = ratio
                            best_r, best_c = r_idx, c_idx
            
            if best_r != -1:
                # Append text to cell
                current = grid[best_r][best_c]
                grid[best_r][best_c] = (current + " " + word['text']).strip()
            
        return grid

