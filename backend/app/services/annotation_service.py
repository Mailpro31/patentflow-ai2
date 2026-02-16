"""
Service d'annotation automatique pour schémas SVG.
Place des labels numérotés sur les composants détectés.
"""

import logging
from typing import List, Dict, Tuple, Optional
import xml.etree.ElementTree as ET
import math

logger = logging.getLogger(__name__)


class AnnotationService:
    """
    Service d'annotation automatique de schémas SVG.
    Place des labels numérotés (10, 20, 30...) sur les composants.
    """
    
    def __init__(self):
        """Initialize annotation service."""
        self.label_font_size = 14
        self.label_font_family = "Arial, sans-serif"
        self.circle_radius = 12
        self.min_label_distance = 25  # Minimum distance between labels
    
    def place_labels_on_svg(
        self,
        svg_content: str,
        components: List[Dict],
        start_number: int = 10,
        increment: int = 10,
        add_leader_lines: bool = True
    ) -> Tuple[str, List[Dict]]:
        """
        Place des labels numérotés sur le SVG.
        
        Args:
            svg_content: Contenu SVG original
            components: Liste de composants détectés
            start_number: Numéro de départ (ex: 10)
            increment: Incrément (ex: 10 pour 10, 20, 30...)
            add_leader_lines: Ajouter lignes de repère
            
        Returns:
            (SVG annoté, liste de labels placés)
        """
        logger.info(f"Placing labels on {len(components)} components")
        
        # Parse SVG
        try:
            svg_root = ET.fromstring(svg_content)
        except ET.ParseError:
            # Si le SVG a un namespace, essayer de le gérer
            svg_root = ET.fromstring(svg_content.replace('xmlns=', 'xmlnamespace='))
        
        # Get SVG dimensions
        width = int(svg_root.get('width', 800))
        height = int(svg_root.get('height', 600))
        
        # Sort components by importance
        sorted_components = self._sort_components_by_importance(components)
        
        # Place labels
        labels = []
        placed_positions = []
        
        for i, component in enumerate(sorted_components):
            label_number = start_number + (i * increment)
            
            # Calculate optimal label position
            bbox = component['bbox']
            component_center = self._calculate_center(bbox)
            
            label_pos = self._calculate_label_position(
                bbox=bbox,
                component_center=component_center,
                existing_positions=placed_positions,
                image_bounds=(width, height)
            )
            
            # Add label to SVG
            self._add_label_to_svg(
                svg_root=svg_root,
                label_number=label_number,
                position=label_pos
            )
            
            # Add leader line if needed
            if add_leader_lines:
                distance = self._distance(label_pos, component_center)
                if distance > 30:  # Only add if label is far from component
                    self._add_leader_line(
                        svg_root=svg_root,
                        from_pos=component_center,
                        to_pos=label_pos
                    )
            
            # Record label
            labels.append({
                'number': label_number,
                'position': list(label_pos),
                'component_id': component['id'],
                'has_leader_line': add_leader_lines and distance > 30
            })
            
            placed_positions.append(label_pos)
        
        # Convert back to string
        annotated_svg = ET.tostring(svg_root, encoding='unicode')
        
        logger.info(f"Placed {len(labels)} labels")
        return annotated_svg, labels
    
    def _sort_components_by_importance(
        self,
        components: List[Dict]
    ) -> List[Dict]:
        """
        Trie les composants par importance.
        
        Criteria:
        1. Area (larger is more important)
        2. Position (top-left to bottom-right)
        """
        def importance_score(comp):
            bbox = comp['bbox']
            x, y, w, h = bbox
            area = comp['area']
            
            # Normalize position (0-1)
            # Prefer top-left (lower scores)
            position_score = (y * 0.3 + x * 0.1) / 1000
            
            # Larger area = higher importance
            area_score = area
            
            return area_score - position_score
        
        return sorted(components, key=importance_score, reverse=True)
    
    def _calculate_center(self, bbox: List[int]) -> Tuple[int, int]:
        """Calcule le centre d'une bbox."""
        x, y, w, h = bbox
        return (x + w // 2, y + h // 2)
    
    def _calculate_label_position(
        self,
        bbox: List[int],
        component_center: Tuple[int, int],
        existing_positions: List[Tuple[int, int]],
        image_bounds: Tuple[int, int]
    ) -> Tuple[int, int]:
        """
        Calcule la position optimale pour un label.
        
        Strategy:
        - Try several candidate positions
        - Choose one that doesn't overlap existing labels
        - Stays within image bounds
        """
        x, y, w, h = bbox
        img_width, img_height = image_bounds
        
        # Candidate positions (in order of preference)
        margin = 15
        candidates = [
            (x + w + margin, y),                    # Right-top
            (x + w + margin, y + h // 2),           # Right-middle
            (x - margin - 30, y),                   # Left-top
            (x + w // 2 - 10, y - margin - 15),     # Top-center
            (x + w // 2 - 10, y + h + margin),      # Bottom-center
            (x + w + margin, y + h),                # Right-bottom
            (x - margin - 30, y + h // 2),          # Left-middle
        ]
        
        # Score each candidate
        for pos_x, pos_y in candidates:
            # Check bounds
            if pos_x < 10 or pos_x > img_width - 30:
                continue
            if pos_y < 15 or pos_y > img_height - 10:
                continue
            
            # Check distance from existing labels
            if self._is_position_clear(
                (pos_x, pos_y),
                existing_positions,
                self.min_label_distance
            ):
                return (pos_x, pos_y)
        
        # Fallback: use first candidate even if overlapping
        return candidates[0]
    
    def _is_position_clear(
        self,
        position: Tuple[int, int],
        existing_positions: List[Tuple[int, int]],
        min_distance: float
    ) -> bool:
        """Vérifie si une position est assez éloignée des labels existants."""
        for existing_pos in existing_positions:
            distance = self._distance(position, existing_pos)
            if distance < min_distance:
                return False
        return True
    
    def _distance(
        self,
        pos1: Tuple[int, int],
        pos2: Tuple[int, int]
    ) -> float:
        """Calcule distance euclidienne entre deux positions."""
        return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
    
    def _add_label_to_svg(
        self,
        svg_root: ET.Element,
        label_number: int,
        position: Tuple[int, int]
    ) -> None:
        """
        Ajoute un label numéroté au SVG.
        Style: cercle blanc avec bordure noire + texte.
        """
        x, y = position
        
        # Create group for label
        group = ET.Element('g', {'class': 'patent-label'})
        
        # Background circle
        circle = ET.Element('circle', {
            'cx': str(x),
            'cy': str(y),
            'r': str(self.circle_radius),
            'fill': 'white',
            'stroke': 'black',
            'stroke-width': '1.5'
        })
        group.append(circle)
        
        # Text element
        text = ET.Element('text', {
            'x': str(x),
            'y': str(y + 5),  # Offset for vertical centering
            'font-family': self.label_font_family,
            'font-size': str(self.label_font_size),
            'font-weight': 'bold',
            'fill': 'black',
            'text-anchor': 'middle',
            'dominant-baseline': 'middle'
        })
        text.text = str(label_number)
        group.append(text)
        
        svg_root.append(group)
    
    def _add_leader_line(
        self,
        svg_root: ET.Element,
        from_pos: Tuple[int, int],
        to_pos: Tuple[int, int]
    ) -> None:
        """
        Ajoute une ligne de repère du composant au label.
        Style: ligne noire pointillée.
        """
        x1, y1 = from_pos
        x2, y2 = to_pos
        
        # Adjust endpoints to not overlap label circle
        # Calculate direction vector and shorten
        dx = x2 - x1
        dy = y2 - y1
        length = math.sqrt(dx*dx + dy*dy)
        
        if length > 0:
            # Shorten by circle radius
            factor = (length - self.circle_radius - 2) / length
            x2_adj = x1 + dx * factor
            y2_adj = y1 + dy * factor
        else:
            x2_adj, y2_adj = x2, y2
        
        line = ET.Element('line', {
            'x1': str(x1),
            'y1': str(y1),
            'x2': str(int(x2_adj)),
            'y2': str(int(y2_adj)),
            'stroke': 'black',
            'stroke-width': '1',
            'stroke-dasharray': '3,3',
            'class': 'leader-line'
        })
        
        svg_root.append(line)


# Instance globale
annotator = AnnotationService()
