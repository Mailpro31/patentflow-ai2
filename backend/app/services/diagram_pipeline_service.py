"""
Pipeline complet de traitement d'images techniques.
Orchestrate: génération SDXL → vectorisation → détection → annotation.
"""

import logging
import time
from typing import Dict, Optional
import io

from app.services.image_generator_service import image_generator
from app.services.vectorization_service import vectorizer
from app.services.component_detector_service import component_detector
from app.services.annotation_service import annotator

logger = logging.getLogger(__name__)


class DiagramPipelineService:
    """
    Pipeline complet de traitement de schémas techniques.
    
    Workflow:
    1. Sketch → Technical Diagram (SDXL + ControlNet)
    2. Diagram → SVG (Potrace)
    3. Detect Components (SAM2)
    4. Annotate SVG (labels numérotés)
    """
    
    def __init__(self):
        """Initialize pipeline service."""
        self.generator = image_generator
        self.vectorizer = vectorizer
        self.detector = component_detector
        self.annotator = annotator
        
        logger.info("DiagramPipelineService initialized")
    
    async def process_sketch(
        self,
        sketch_bytes: bytes,
        diagram_type: str = "generic",
        auto_annotate: bool = True,
        start_number: int = 10,
        number_increment: int = 10,
        controlnet_strength: float = 0.8,
        add_leader_lines: bool = True,
        custom_prompt: Optional[str] = None
    ) -> Dict:
        """
        Pipeline complet de traitement de croquis.
        
        Args:
            sketch_bytes: Image du croquis (bytes)
            diagram_type: Type de schéma (mechanical, electrical, etc.)
            auto_annotate: Activer annotation automatique
            start_number: Numéro de départ pour labels
            number_increment: Incrément entre labels
            controlnet_strength: Force du ControlNet (0-1)
            add_leader_lines: Ajouter lignes de repère
            custom_prompt: Prompt personnalisé (optionnel)
            
        Returns:
            Dictionnaire avec SVG annoté, metadata, composants, labels
        """
        start_time = time.time()
        
        logger.info(f"Starting pipeline for {diagram_type} diagram")
        
        # Step 1: Generate technical diagram with SDXL
        logger.info("Step 1/4: Generating technical diagram with SDXL + ControlNet")
        diagram_bytes = await self.generator.generate_technical_diagram(
            sketch_image=sketch_bytes,
            diagram_type=diagram_type,
            controlnet_strength=controlnet_strength,
            custom_prompt=custom_prompt
        )
        
        # Step 2: Vectorize to SVG
        logger.info("Step 2/4: Vectorizing diagram to SVG with Potrace")
        svg_content = self.vectorizer.bitmap_to_svg(diagram_bytes)
        svg_optimized = self.vectorizer.optimize_svg(svg_content)
        
        # If no annotation, return early
        if not auto_annotate:
            processing_time = int((time.time() - start_time) * 1000)
            
            return {
                'svg_content': svg_optimized,
                'diagram_image': diagram_bytes,
                'components': [],
                'labels': [],
                'processing_time_ms': processing_time,
                'auto_annotated': False
            }
        
        # Step 3: Detect components
        logger.info("Step 3/4: Detecting components with SAM2")
        components = await self.detector.detect_components(
            image_bytes=diagram_bytes,
            min_area=100,
            max_components=50
        )
        
        # Step 4: Annotate SVG
        logger.info("Step 4/4: Adding automatic labels to SVG")
        annotated_svg, labels = self.annotator.place_labels_on_svg(
            svg_content=svg_optimized,
            components=components,
            start_number=start_number,
            increment=number_increment,
            add_leader_lines=add_leader_lines
        )
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # Prepare response
        result = {
            'svg_content': annotated_svg,
            'diagram_image': diagram_bytes,
            'components': [
                {
                    'id': comp['id'],
                    'bbox': comp['bbox'],
                    'area': comp['area'],
                    'type': comp.get('type', 'unknown')
                }
                for comp in components
            ],
            'labels': labels,
            'processing_time_ms': processing_time,
            'auto_annotated': True,
            'quality_metrics': {
                'num_components_detected': len(components),
                'num_labels_placed': len(labels),
                'avg_component_area': sum(c['area'] for c in components) / len(components) if components else 0
            }
        }
        
        logger.info(
            f"Pipeline complete: {len(components)} components, "
            f"{len(labels)} labels, {processing_time}ms"
        )
        
        return result
    
    async def vectorize_only(
        self,
        image_bytes: bytes,
        threshold: int = 128,
        optimize: bool = True
    ) -> str:
        """
        Vectorise une image sans génération ni annotation.
        
        Args:
            image_bytes: Image à vectoriser
            threshold: Seuil de binarisation
            optimize: Optimiser le SVG
            
        Returns:
            Contenu SVG
        """
        logger.info("Vectorize-only mode")
        
        svg_content = self.vectorizer.bitmap_to_svg(
            image_bytes=image_bytes,
            threshold=threshold
        )
        
        if optimize:
            svg_content = self.vectorizer.optimize_svg(svg_content)
        
        return svg_content
    
    async def annotate_existing_svg(
        self,
        svg_content: str,
        reference_image: bytes,
        start_number: int = 10,
        number_increment: int = 10,
        add_leader_lines: bool = True
    ) -> Dict:
        """
        Ajoute annotations à un SVG existant.
        
        Args:
            svg_content: SVG existant
            reference_image: Image pour détection de composants
            start_number: Numéro de départ
            number_increment: Incrément
            add_leader_lines: Ajouter lignes de repère
            
        Returns:
            SVG annoté + metadata
        """
        logger.info("Annotating existing SVG")
        
        # Detect components in reference image
        components = await self.detector.detect_components(
            image_bytes=reference_image,
            min_area=100
        )
        
        # Annotate SVG
        annotated_svg, labels = self.annotator.place_labels_on_svg(
            svg_content=svg_content,
            components=components,
            start_number=start_number,
            increment=number_increment,
            add_leader_lines=add_leader_lines
        )
        
        return {
            'svg_content': annotated_svg,
            'labels': labels,
            'num_components': len(components)
        }


# Instance globale
diagram_pipeline = DiagramPipelineService()
