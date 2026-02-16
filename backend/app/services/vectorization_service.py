"""
Service de vectorisation d'images bitmap en SVG avec Potrace.
"""

import logging
import io
from typing import Optional
from PIL import Image
import numpy as np
import pypotrace
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


class VectorizationService:
    """
    Service de conversion bitmap → SVG avec Potrace.
    Optimisé pour schémas techniques de brevets.
    """
    
    def __init__(self):
        """Initialize vectorization service."""
        self.default_params = {
            "turnpolicy": "minority",
            "turdsize": 2,
            "alphamax": 1.0,
            "opticurve": True,
            "opttolerance": 0.2
        }
    
    def bitmap_to_svg(
        self,
        image_bytes: bytes,
        threshold: int = 128,
        invert: bool = False
    ) -> str:
        """
        Convertit image bitmap en SVG vectorisé.
        
        Args:
            image_bytes: Image source (bytes)
            threshold: Seuil de binarisation (0-255)
            invert: Inverser noir/blanc
            
        Returns:
            Contenu SVG (string)
        """
        logger.info("Starting bitmap to SVG vectorization")
        
        # Load image
        img = Image.open(io.BytesIO(image_bytes))
        width, height = img.size
        
        # Convert to grayscale
        img_gray = img.convert('L')
        
        # Binarize
        img_bw = img_gray.point(lambda x: 255 if x > threshold else 0, '1')
        
        if invert:
            img_bw = img_bw.point(lambda x: 255 - x)
        
        # Convert to numpy array for Potrace
        bitmap_array = np.array(img_bw, dtype=bool)
        
        # Create Potrace bitmap
        bmp = pypotrace.Bitmap(bitmap_array)
        
        # Trace paths
        path = bmp.trace(
            turdsize=self.default_params["turdsize"],
            turnpolicy=self.default_params["turnpolicy"],
            alphamax=self.default_params["alphamax"],
            opticurve=self.default_params["opticurve"],
            opttolerance=self.default_params["opttolerance"]
        )
        
        # Convert to SVG
        svg_content = self._path_to_svg(path, width, height)
        
        logger.info(f"Vectorization complete: {len(svg_content)} bytes SVG")
        return svg_content
    
    def _path_to_svg(self, path, width: int, height: int) -> str:
        """
        Convertit Potrace path en SVG.
        """
        # Create SVG root
        svg = ET.Element('svg', {
            'xmlns': 'http://www.w3.org/2000/svg',
            'width': str(width),
            'height': str(height),
            'viewBox': f'0 0 {width} {height}',
            'version': '1.1'
        })
        
        # Add paths
        for curve in path:
            path_data = []
            
            # Start point
            start_point = curve.start_point
            path_data.append(f'M {start_point.x},{start_point.y}')
            
            # Segments
            for segment in curve.segments:
                if segment.is_corner:
                    # Line segment
                    c = segment.c
                    path_data.append(f'L {c.x},{c.y}')
                    end = segment.end_point
                    path_data.append(f'L {end.x},{end.y}')
                else:
                    # Bezier curve
                    c1 = segment.c1
                    c2 = segment.c2
                    end = segment.end_point
                    path_data.append(
                        f'C {c1.x},{c1.y} {c2.x},{c2.y} {end.x},{end.y}'
                    )
            
            # Close path
            path_data.append('Z')
            
            # Create path element
            path_elem = ET.Element('path', {
                'd': ' '.join(path_data),
                'fill': 'black',
                'stroke': 'none'
            })
            svg.append(path_elem)
        
        # Convert to string
        svg_string = ET.tostring(svg, encoding='unicode')
        return svg_string
    
    def optimize_svg(self, svg_content: str) -> str:
        """
        Optimise SVG pour réduire taille et améliorer qualité.
        
        Uses scour if available, otherwise basic optimization.
        """
        try:
            import scour.scour
            
            options = scour.scour.sanitizeOptions()
            options.strip_xml_prolog = True
            options.remove_metadata = True
            options.indent_type = 'space'
            options.indent_depth = 2
            options.newlines = True
            options.strip_comments = True
            options.remove_descriptive_elements = True
            
            optimized = scour.scour.scourString(svg_content, options)
            logger.info("SVG optimized with scour")
            return optimized
            
        except ImportError:
            logger.warning("scour not available, using basic optimization")
            return self._basic_svg_optimization(svg_content)
    
    def _basic_svg_optimization(self, svg_content: str) -> str:
        """Basic SVG optimization without scour."""
        # Parse SVG
        root = ET.fromstring(svg_content)
        
        # Remove comments
        for elem in root.iter():
            if elem.tag is ET.Comment:
                root.remove(elem)
        
        # Pretty print
        self._indent_xml(root)
        
        return ET.tostring(root, encoding='unicode')
    
    def _indent_xml(self, elem, level=0):
        """Add indentation to XML for readability."""
        indent = "\n" + "  " * level
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = indent + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = indent
            for child in elem:
                self._indent_xml(child, level + 1)
            if not child.tail or not child.tail.strip():
                child.tail = indent
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = indent


# Instance globale
vectorizer = VectorizationService()
