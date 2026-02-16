"""
Service de détection de composants avec SAM2 (Segment Anything Model 2).
Détecte automatiquement tous les composants dans un schéma technique.
"""

import logging
from typing import List, Dict, Optional, Tuple
import io
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class ComponentDetectorService:
    """
    Service de détection automatique de composants avec SAM2.
    Identifie tous les éléments distincts dans un schéma technique.
    """
    
    def __init__(self):
        """Initialize SAM2 detector."""
        self.model = None
        self.predictor = None
        self._initialized = False
        
        logger.info("ComponentDetectorService initialized (lazy loading)")
    
    def _lazy_load_model(self):
        """
        Charge SAM2 model à la première utilisation.
        Lazy loading pour éviter temps de démarrage long.
        """
        if self._initialized:
            return
        
        try:
            # NOTE: SAM2 requires manual installation
            # pip install git+https://github.com/facebookresearch/segment-anything-2.git
            from sam2.build_sam import build_sam2
            from sam2.automatic_mask_generator import SAM2AutomaticMaskGenerator
            
            # Load SAM2 model
            checkpoint = "sam2_hiera_large.pt"  # Or other variant
            model_cfg = "sam2_hiera_l.yaml"
            
            sam2 = build_sam2(model_cfg, checkpoint, device="cpu")  # Use cuda if available
            
            self.mask_generator = SAM2AutomaticMaskGenerator(
                model=sam2,
                points_per_side=32,
                pred_iou_thresh=0.86,
                stability_score_thresh=0.92,
                crop_n_layers=1,
                crop_n_points_downscale_factor=2,
                min_mask_region_area=100
            )
            
            self._initialized = True
            logger.info("SAM2 model loaded successfully")
            
        except ImportError as e:
            logger.warning(f"SAM2 not available: {e}. Using fallback detection.")
            self._initialized = False
        except Exception as e:
            logger.error(f"Error loading SAM2: {e}")
            self._initialized = False
    
    async def detect_components(
        self,
        image_bytes: bytes,
        min_area: int = 100,
        max_components: int = 50
    ) -> List[Dict]:
        """
        Détecte tous les composants dans l'image.
        
        Args:
            image_bytes: Image à analyser
            min_area: Aire minimale d'un composant (pixels)
            max_components: Nombre max de composants à retourner
            
        Returns:
            Liste de composants détectés avec masques et bboxes
        """
        logger.info("Detecting components in image")
        
        # Load image
        img = Image.open(io.BytesIO(image_bytes))
        img_array = np.array(img.convert('RGB'))
        
        # Lazy load model
        self._lazy_load_model()
        
        # Detect with SAM2 or fallback
        if self._initialized and self.mask_generator:
            components = await self._detect_with_sam2(img_array, min_area)
        else:
            components = self._detect_with_fallback(img_array, min_area)
        
        # Sort by area (largest first) and limit
        components_sorted = sorted(
            components,
            key=lambda x: x['area'],
            reverse=True
        )[:max_components]
        
        logger.info(f"Detected {len(components_sorted)} components")
        return components_sorted
    
    async def _detect_with_sam2(
        self,
        image_array: np.ndarray,
        min_area: int
    ) -> List[Dict]:
        """
        Détecte avec SAM2 (mode automatique).
        """
        # Generate masks
        masks = self.mask_generator.generate(image_array)
        
        # Filter and format
        components = []
        for i, mask in enumerate(masks):
            area = mask['area']
            
            if area < min_area:
                continue
            
            # Extract bbox [x, y, width, height]
            bbox = mask['bbox']
            
            components.append({
                'id': i,
                'mask': mask['segmentation'],
                'bbox': bbox,
                'area': area,
                'predicted_iou': mask.get('predicted_iou', 0.0),
                'stability_score': mask.get('stability_score', 0.0),
                'type': self._classify_component(bbox)
            })
        
        return components
    
    def _detect_with_fallback(
        self,
        image_array: np.ndarray,
        min_area: int
    ) -> List[Dict]:
        """
        Détection de secours avec OpenCV (si SAM2 indisponible).
        Utilise contour detection classique.
        """
        try:
            import cv2
            
            # Convert to grayscale
            gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
            
            # Threshold
            _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
            
            # Find contours
            contours, _ = cv2.findContours(
                binary,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE
            )
            
            components = []
            for i, contour in enumerate(contours):
                area = cv2.contourArea(contour)
                
                if area < min_area:
                    continue
                
                # Get bounding box
                x, y, w, h = cv2.boundingRect(contour)
                
                # Create mask
                mask = np.zeros(image_array.shape[:2], dtype=np.uint8)
                cv2.drawContours(mask, [contour], -1, 255, -1)
                
                components.append({
                    'id': i,
                    'mask': mask > 0,
                    'bbox': [x, y, w, h],
                    'area': int(area),
                    'predicted_iou': 0.5,
                    'stability_score': 0.5,
                    'type': self._classify_component([x, y, w, h])
                })
            
            logger.info(f"Fallback detection found {len(components)} components")
            return components
            
        except ImportError:
            logger.error("OpenCV not available, cannot detect components")
            return []
    
    def _classify_component(self, bbox: List[int]) -> str:
        """
        Classifie le type de composant basé sur sa forme.
        
        Simple heuristics based on aspect ratio.
        """
        x, y, w, h = bbox
        
        if h == 0:
            return "unknown"
        
        aspect_ratio = w / h
        
        if 0.9 < aspect_ratio < 1.1:
            return "circular"
        elif aspect_ratio > 2.5:
            return "horizontal"
        elif aspect_ratio < 0.4:
            return "vertical"
        elif aspect_ratio > 1.5:
            return "rectangular_h"
        elif aspect_ratio < 0.67:
            return "rectangular_v"
        else:
            return "square"
    
    def calculate_component_center(self, bbox: List[int]) -> Tuple[int, int]:
        """Calcule le centre d'un composant."""
        x, y, w, h = bbox
        return (x + w // 2, y + h // 2)


# Instance globale
component_detector = ComponentDetectorService()
