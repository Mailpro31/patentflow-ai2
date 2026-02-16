"""Mode de génération pour les documents de brevet."""

from enum import Enum


class GenerationMode(str, Enum):
    """Modes de génération de documents de brevet."""
    LARGE = "large"
    TECHNIQUE = "technique"
    INPI_COMPLIANCE = "inpi_compliance"
