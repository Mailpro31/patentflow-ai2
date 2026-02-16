"""
Service de génération de documents de brevet avec Gemini 1.5 Pro.
"""

import google.generativeai as genai
from typing import Optional, Dict, List
import logging
from app.config import settings
from app.models.generation_mode import GenerationMode
from app.services.prompts.patent_engineer_prompts import (
    get_full_system_prompt,
    get_mode_config
)
from app.services.text_linter import patent_linter

logger = logging.getLogger(__name__)


class AIWriterService:
    """
    Service de génération de documents de brevet avec Gemini 1.5 Pro.
    Intègre les prompts d'ingénieur brevet et le post-traitement.
    """
    
    def __init__(self):
        """Initialize Gemini API."""
        self.api_key = settings.GEMINI_API_KEY
        if self.api_key:
            genai.configure(api_key=self.api_key)
            logger.info("Gemini API configured successfully")
        else:
            logger.warning("No Gemini API key configured")
    
    async def generate_patent_document(
        self,
        idea_description: str,
        technical_details: Optional[str] = None,
        mode: GenerationMode = GenerationMode.TECHNIQUE,
        language: str = "fr",
        auto_lint: bool = True
    ) -> Dict:
        """
        Génère un document de brevet complet.
        
        Args:
            idea_description: Description de l'idée brute
            technical_details: Détails techniques optionnels
            mode: Mode de génération
            language: Langue (fr ou en)
            auto_lint: Appliquer post-traitement automatique
            
        Returns:
            Dict avec document généré et métadonnées
        """
        logger.info(f"Generating patent document in {mode.value} mode")
        
        # Construire le prompt utilisateur
        user_prompt = self._build_user_prompt(
            idea_description,
            technical_details,
            language
        )
        
        # Obtenir le prompt système pour ce mode
        system_prompt = get_full_system_prompt(mode)
        mode_config = get_mode_config(mode)
        
        # Générer avec Gemini
        try:
            raw_document = await self._generate_with_gemini(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=mode_config['temperature'],
                top_p=mode_config['top_p'],
                max_tokens=mode_config['max_tokens']
            )
            
            # Parser le document généré
            parsed = self._parse_generated_document(raw_document)
            
            # Appliquer linter si demandé
            if auto_lint:
                lint_result = patent_linter.lint_document(
                    title=parsed['title'],
                    abstract=parsed['abstract'],
                    description=parsed['description'],
                    claims=parsed['claims'],
                    auto_fix=True
                )
                
                return {
                    'title': lint_result['linted']['title'],
                    'abstract': lint_result['linted']['abstract'],
                    'description': lint_result['linted']['description'],
                    'claims': lint_result['linted']['claims'],
                    'quality_score': lint_result['quality_score'],
                    'modifications': lint_result['modifications'],
                    'validations': lint_result['validations'],
                    'mode_used': mode.value,
                    'raw_output': raw_document
                }
            else:
                return {
                    **parsed,
                    'quality_score': None,
                    'modifications': [],
                    'validations': {},
                    'mode_used': mode.value,
                    'raw_output': raw_document
                }
                
        except Exception as e:
            logger.error(f"Error generating patent document: {e}")
            raise
    
    def _build_user_prompt(
        self,
        idea_description: str,
        technical_details: Optional[str],
        language: str
    ) -> str:
        """Construit le prompt utilisateur."""
        prompt = f"""Génère un document de brevet complet à partir de l'idée suivante.

## IDÉE À BREVETER

{idea_description}
"""
        
        if technical_details:
            prompt += f"""
## DÉTAILS TECHNIQUES SUPPLÉMENTAIRES

{technical_details}
"""
        
        prompt += f"""
## FORMAT DE SORTIE ATTENDU

Génère un document structuré avec les sections suivantes, clairement séparées:

**TITRE:**
[Titre du brevet]

**ABRÉGÉ:**
[Abrégé de 100-150 mots]

**DESCRIPTION:**
[Description complète avec numérotation [0001], [0002]... si mode INPI]

**REVENDICATIONS:**
[Revendications numérotées 1., 2., 3...]

IMPORTANT:
- Langue: {language}
- Respecter toutes les règles de rédaction de brevets
- Utiliser "caractérisé en ce que" dans les revendications principales
- Utiliser "comprenant" pour les listes
- Éviter adjectifs subjectifs (meilleur, optimal...)
- Numéroter tous les éléments avec références croisées
"""
        
        return prompt
    
    async def _generate_with_gemini(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        top_p: float,
        max_tokens: int
    ) -> str:
        """
        Appelle Gemini API pour générer le texte.
        
        Args:
            system_prompt: Instruction système
            user_prompt: Prompt utilisateur
            temperature: Température de génération
            top_p: Top-p sampling
            max_tokens: Nombre max de tokens
            
        Returns:
            Texte généré
        """
        try:
            # Configuration du modèle
            model = genai.GenerativeModel(
                model_name=settings.GEMINI_MODEL,
                generation_config={
                    'temperature': temperature,
                    'top_p': top_p,
                    'max_output_tokens': max_tokens,
                },
                system_instruction=system_prompt
            )
            
            # Génération
            response = model.generate_content(user_prompt)
            
            if not response or not response.text:
                raise ValueError("Empty response from Gemini")
            
            logger.info(f"Generated {len(response.text)} characters")
            return response.text
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise
    
    def _parse_generated_document(self, raw_text: str) -> Dict[str, str]:
        """
        Parse le document généré pour extraire les sections.
        
        Args:
            raw_text: Texte brut généré
            
        Returns:
            Dict avec sections séparées
        """
        import re
        
        result = {
            'title': '',
            'abstract': '',
            'description': '',
            'claims': ''
        }
        
        # Extraire le titre
        title_match = re.search(
            r'\*\*TITRE:\*\*\s*(.+?)(?=\*\*|\n\n)',
            raw_text,
            re.DOTALL
        )
        if title_match:
            result['title'] = title_match.group(1).strip()
        
        # Extraire l'abrégé
        abstract_match = re.search(
            r'\*\*ABRÉGÉ:\*\*\s*(.+?)(?=\*\*)',
            raw_text,
            re.DOTALL
        )
        if abstract_match:
            result['abstract'] = abstract_match.group(1).strip()
        
        # Extraire la description
        desc_match = re.search(
            r'\*\*DESCRIPTION:\*\*\s*(.+?)(?=\*\*REVENDICATIONS:)',
            raw_text,
            re.DOTALL
        )
        if desc_match:
            result['description'] = desc_match.group(1).strip()
        
        # Extraire les revendications
        claims_match = re.search(
            r'\*\*REVENDICATIONS:\*\*\s*(.+?)(?=\*\*|$)',
            raw_text,
            re.DOTALL
        )
        if claims_match:
            result['claims'] = claims_match.group(1).strip()
        
        return result
    
    async def generate_section(
        self,
        section_type: str,
        context: str,
        mode: GenerationMode = GenerationMode.TECHNIQUE
    ) -> str:
        """
        Génère une section spécifique du brevet.
        
        Args:
            section_type: Type de section (description, claims, abstract)
            context: Contexte pour la génération
            mode: Mode de génération
            
        Returns:
            Texte de la section générée
        """
        system_prompt = get_full_system_prompt(mode)
        mode_config = get_mode_config(mode)
        
        user_prompt = f"""Génère uniquement la section {section_type.upper()} d'un brevet basé sur:

{context}

Retourne uniquement le contenu de cette section, sans titre ni marqueurs.
"""
        
        text = await self._generate_with_gemini(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=mode_config['temperature'],
            top_p=mode_config['top_p'],
            max_tokens=mode_config['max_tokens']
        )
        
        return text.strip()
    
    async def refine_document(
        self,
        existing_document: Dict[str, str],
        refinement_instructions: str
    ) -> Dict:
        """
        Raffine un document existant selon des instructions.
        
        Args:
            existing_document: Document avec title, abstract, description, claims
            refinement_instructions: Instructions de raffinement
            
        Returns:
            Document raffiné
        """
        system_prompt = get_full_system_prompt(GenerationMode.TECHNIQUE)
        
        user_prompt = f"""Raffine le document de brevet suivant selon ces instructions:

{refinement_instructions}

DOCUMENT ACTUEL:

**TITRE:**
{existing_document['title']}

**ABRÉGÉ:**
{existing_document['abstract']}

**DESCRIPTION:**
{existing_document['description']}

**REVENDICATIONS:**
{existing_document['claims']}

Retourne le document complet raffiné dans le même format.
"""
        
        refined_text = await self._generate_with_gemini(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
            top_p=0.9,
            max_tokens=8192
        )
        
        parsed = self._parse_generated_document(refined_text)
        
        # Appliquer linter
        lint_result = patent_linter.lint_document(
            title=parsed['title'],
            abstract=parsed['abstract'],
            description=parsed['description'],
            claims=parsed['claims'],
            auto_fix=True
        )
        
        return {
            'title': lint_result['linted']['title'],
            'abstract': lint_result['linted']['abstract'],
            'description': lint_result['linted']['description'],
            'claims': lint_result['linted']['claims'],
            'quality_score': lint_result['quality_score'],
            'modifications': lint_result['modifications']
        }


# Instance globale
ai_writer = AIWriterService()
