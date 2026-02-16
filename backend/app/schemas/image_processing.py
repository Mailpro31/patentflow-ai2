"""
Pydantic schemas pour traitement d'images et génération de schémas.
"""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from uuid import UUID


class ComponentInfo(BaseModel):
    """Information sur un composant détecté."""
    id: int
    bbox: List[int] = Field(..., description="[x, y, width, height]")
    area: int
    type: str = Field(default="unknown")


class LabelInfo(BaseModel):
    """Information sur un label placé."""
    number: int
    position: List[int] = Field(..., description="[x, y]")
    component_id: int
    has_leader_line: bool = False


class DiagramGenerationRequest(BaseModel):
    """Requête de génération de schéma technique."""
    
    sketch_image: str = Field(
        ...,
        description="Image du croquis encodée en base64"
    )
    
    diagram_type: str = Field(
        default="generic",
        pattern="^(mechanical|electrical|chemical|software|generic)$",
        description="Type de schéma technique"
    )
    
    auto_annotate: bool = Field(
        default=True,
        description="Activer annotation automatique"
    )
    
    start_number: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Numéro de départ pour labels"
    )
    
    number_increment: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Incrément entre labels (ex: 10 pour 10, 20, 30...)"
    )
    
    controlnet_strength: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Force du ControlNet (0.0 = ignore sketch, 1.0 = follow exactly)"
    )
    
    add_leader_lines: bool = Field(
        default=True,
        description="Ajouter lignes de repère reliant labels aux composants"
    )
    
    custom_prompt: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Prompt personnalisé pour la génération (optionnel)"
    )
    
    project_id: Optional[UUID] = Field(
        default=None,
        description="ID du projet associé (optionnel)"
    )


class DiagramGenerationResponse(BaseModel):
    """Réponse de génération de schéma."""
    
    diagram_id: Optional[UUID] = None
    svg_content: str
    diagram_image_url: str
    
    components: List[ComponentInfo]
    labels: List[LabelInfo]
    
    processing_time_ms: int
    auto_annotated: bool
    
    quality_metrics: Dict = Field(
        default_factory=dict,
        description="Métriques de qualité (nombre composants, etc.)"
    )


class VectorizationRequest(BaseModel):
    """Requête de vectorisation seule."""
    
    image: str = Field(
        ...,
        description="Image à vectoriser (base64)"
    )
    
    threshold: int = Field(
        default=128,
        ge=0,
        le=255,
        description="Seuil de binarisation"
    )
    
    optimize: bool = Field(
        default=True,
        description="Optimiser le SVG généré"
    )


class VectorizationResponse(BaseModel):
    """Réponse de vectorisation."""
    
    svg_content: str
    optimization_applied: bool


class AnnotationRequest(BaseModel):
    """Requête d'annotation d'un SVG existant."""
    
    svg_content: str = Field(
        ...,
        description="Contenu SVG à annoter"
    )
    
    reference_image: str = Field(
        ...,
        description="Image de référence pour détection de composants (base64)"
    )
    
    start_number: int = Field(default=10, ge=1, le=100)
    number_increment: int = Field(default=10, ge=1, le=50)
    add_leader_lines: bool = True


class AnnotationResponse(BaseModel):
    """Réponse d'annotation."""
    
    svg_content: str
    labels: List[LabelInfo]
    num_components: int


class DiagramTypeInfo(BaseModel):
    """Information sur un type de schéma disponible."""
    
    type: str
    name: str
    description: str
    optimal_use_cases: List[str]
    example_prompt: str


class DiagramTypesResponse(BaseModel):
    """Liste des types de schémas disponibles."""
    
    types: List[DiagramTypeInfo]
