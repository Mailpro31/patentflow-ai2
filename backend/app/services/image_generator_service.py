"""
Service de génération d'images techniques avec Stable Diffusion SDXL + ControlNet.
Transforme des croquis en schémas techniques professionnels.
"""

import logging
import io
import base64
from typing import Optional, Dict
import replicate
from PIL import Image
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


# Prompts optimisés par type de schéma
TECHNICAL_DIAGRAM_PROMPTS = {
    "mechanical": (
        "technical mechanical patent diagram, clean engineering lines, "
        "isometric view, labeled components, professional CAD style, "
        "precise technical drawing, black and white line art"
    ),
    "electrical": (
        "electrical circuit diagram, clean schematic symbols, "
        "professional engineering drawing, clear connections, "
        "standard electrical notation, technical illustration"
    ),
    "chemical": (
        "chemical process diagram, clean flowchart, professional "
        "industrial drawing, labeled equipment, process flow diagram, "
        "technical engineering style"
    ),
    "software": (
        "software architecture diagram, clean UML style, professional "
        "technical illustration, clear components, system diagram, "
        "technical documentation style"
    ),
    "generic": (
        "technical patent diagram, clean lines, professional engineering "
        "schematic, precise technical drawing, labeled components"
    )
}


class ImageGeneratorService:
    """
    Service de génération d'images techniques avec SDXL + ControlNet.
    Support Replicate API et Stability AI API.
    """
    
    def __init__(self):
        """Initialize image generator with API keys."""
        self.provider = settings.SD_API_PROVIDER
        
        if self.provider == "replicate":
            if settings.REPLICATE_API_KEY:
                replicate.Client(api_token=settings.REPLICATE_API_KEY)
                logger.info("Replicate API configured")
            else:
                logger.warning("No Replicate API key configured")
        elif self.provider == "stability_ai":
            if not settings.STABILITY_AI_API_KEY:
                logger.warning("No Stability AI API key configured")
    
    async def generate_technical_diagram(
        self,
        sketch_image: bytes,
        diagram_type: str = "generic",
        controlnet_strength: float = 0.8,
        custom_prompt: Optional[str] = None
    ) -> bytes:
        """
        Génère un schéma technique professionnel depuis un croquis.
        
        Args:
            sketch_image: Image du croquis (bytes)
            diagram_type: Type de schéma (mechanical, electrical, etc.)
            controlnet_strength: Force du ControlNet (0.0-1.0)
            custom_prompt: Prompt personnalisé (optionnel)
            
        Returns:
            Image du schéma généré (bytes)
        """
        logger.info(f"Generating {diagram_type} diagram with {self.provider}")
        
        # Prétraitement de l'image
        preprocessed = self._preprocess_sketch(sketch_image)
        
        # Choisir le prompt
        prompt = custom_prompt or TECHNICAL_DIAGRAM_PROMPTS.get(
            diagram_type,
            TECHNICAL_DIAGRAM_PROMPTS["generic"]
        )
        
        # Ajouter negative prompt pour améliorer qualité
        negative_prompt = (
            "blurry, low quality, photo, photorealistic, colored, "
            "messy lines, unclear, hand-drawn sketch, rough draft"
        )
        
        # Générer selon le provider
        if self.provider == "replicate":
            result_bytes = await self._generate_with_replicate(
                sketch_image=preprocessed,
                prompt=prompt,
                negative_prompt=negative_prompt,
                controlnet_strength=controlnet_strength
            )
        elif self.provider == "stability_ai":
            result_bytes = await self._generate_with_stability_ai(
                sketch_image=preprocessed,
                prompt=prompt,
                controlnet_strength=controlnet_strength
            )
        else:
            raise ValueError(f"Unknown SD provider: {self.provider}")
        
        logger.info(f"Generated diagram: {len(result_bytes)} bytes")
        return result_bytes
    
    def _preprocess_sketch(self, image_bytes: bytes) -> bytes:
        """
        Prétraite le croquis pour optimiser la génération.
        
        - Resize si trop grand
        - Convert to RGB
        - Normalize
        """
        img = Image.open(io.BytesIO(image_bytes))
        
        # Resize si nécessaire (max 1024x1024 pour SDXL)
        max_size = 1024
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = tuple(int(dim * ratio) for dim in img.size)
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            logger.info(f"Resized image to {new_size}")
        
        # Convert to RGB si nécessaire
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Save to bytes
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    async def _generate_with_replicate(
        self,
        sketch_image: bytes,
        prompt: str,
        negative_prompt: str,
        controlnet_strength: float
    ) -> bytes:
        """
        Génère avec Replicate API.
        
        Uses stability-ai/sdxl with controlnet.
        """
        try:
            # Convert image to base64 data URI
            img_b64 = base64.b64encode(sketch_image).decode()
            data_uri = f"data:image/png;base64,{img_b64}"
            
            # Run SDXL with ControlNet
            output = replicate.run(
                settings.SD_MODEL,
                input={
                    "image": data_uri,
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "num_inference_steps": settings.SD_NUM_INFERENCE_STEPS,
                    "guidance_scale": settings.SD_GUIDANCE_SCALE,
                    "controlnet_conditioning_scale": controlnet_strength,
                }
            )
            
            # Output is URL or list of URLs
            if isinstance(output, list):
                image_url = output[0]
            else:
                image_url = output
            
            # Download generated image
            async with httpx.AsyncClient() as client:
                response = await client.get(image_url)
                response.raise_for_status()
                return response.content
                
        except Exception as e:
            logger.error(f"Replicate API error: {e}")
            raise
    
    async def _generate_with_stability_ai(
        self,
        sketch_image: bytes,
        prompt: str,
        controlnet_strength: float
    ) -> bytes:
        """
        Génère avec Stability AI API.
        
        Uses sketch-to-image endpoint.
        """
        try:
            url = "https://api.stability.ai/v2beta/stable-image/control/sketch"
            
            headers = {
                "Authorization": f"Bearer {settings.STABILITY_AI_API_KEY}",
                "Accept": "image/*"
            }
            
            files = {
                "image": ("sketch.png", sketch_image, "image/png")
            }
            
            data = {
                "prompt": prompt,
                "control_strength": controlnet_strength,
                "output_format": "png"
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    files=files,
                    data=data
                )
                response.raise_for_status()
                return response.content
                
        except Exception as e:
            logger.error(f"Stability AI API error: {e}")
            raise
    
    def encode_image_base64(self, image_bytes: bytes) -> str:
        """Encode image to base64 string."""
        return base64.b64encode(image_bytes).decode('utf-8')
    
    def decode_image_base64(self, base64_string: str) -> bytes:
        """Decode base64 string to image bytes."""
        return base64.b64decode(base64_string)


# Instance globale
image_generator = ImageGeneratorService()
