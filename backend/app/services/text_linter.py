"""
Text Linter pour valider et améliorer les documents de brevet générés.
Vérifie les mots-clés obligatoires et supprime les adjectifs non-techniques.
"""

import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class PatentSection(str, Enum):
    """Sections d'un document de brevet."""
    TITLE = "title"
    ABSTRACT = "abstract"
    DESCRIPTION = "description"
    CLAIMS = "claims"


@dataclass
class ValidationResult:
    """Résultat de validation d'un texte."""
    is_valid: bool
    missing_keywords: List[str]
    found_keywords: List[str]
    issues: List[str]
    suggestions: List[str]


@dataclass
class QualityScore:
    """Score de qualité d'un document de brevet."""
    overall_score: int  # 0-100
    keyword_score: int  # 0-100
    language_score: int  # 0-100
    structure_score: int  # 0-100
    technical_clarity_score: int  # 0-100
    details: Dict[str, any]


class PatentTextLinter:
    """
    Analyseur et validateur de texte pour documents de brevet.
    Vérifie les mots-clés obligatoires et élimine les adjectifs subjectifs.
    """
    
    # Mots-clés obligatoires par section
    REQUIRED_KEYWORDS = {
        PatentSection.CLAIMS: [
            "caractérisé en ce que",
            "comprenant"
        ],
        PatentSection.DESCRIPTION: [
            "invention",
            "mode de réalisation"
        ],
        PatentSection.ABSTRACT: [
            "invention"
        ]
    }
    
    # Mots-clés recommandés pour améliorer la qualité
    RECOMMENDED_KEYWORDS = {
        PatentSection.DESCRIPTION: [
            "figure",
            "référence",
            "selon l'invention"
        ],
        PatentSection.CLAIMS: [
            "selon la revendication",
            "dans lequel"
        ]
    }
    
    # Adjectifs non-techniques à supprimer
    NON_TECHNICAL_ADJECTIVES = [
        # Superlatifs absolus
        "meilleur", "meilleure", "meilleurs", "meilleures",
        "optimal", "optimale", "optimaux", "optimales",
        "idéal", "idéale", "idéaux", "idéales",
        "parfait", "parfaite", "parfaits", "parfaites",
        
        # Qualificatifs subjectifs
        "excellent", "excellente", "excellents", "excellentes",
        "remarquable", "remarquables",
        "exceptionnel", "exceptionnelle", "exceptionnels", "exceptionnelles",
        "supérieur", "supérieure", "supérieurs", "supérieures",
        "inférieur", "inférieure", "inférieurs", "inférieures",
        
        # Termes marketing
        "magnifique", "magnifiques",
        "merveilleux", "merveilleuse", "merveilleux", "merveilleuses",
        "formidable", "formidables",
        "fantastique", "fantastiques",
        "incroyable", "incroyables",
        "extraordinaire", "extraordinaires",
        
        # Jugements de valeur
        "simple", "simples",  # Peut nuire à l'activité inventive
        "facile", "faciles",
        "évident", "évidente", "évidents", "évidentes",
        "trivial", "triviale", "triviaux", "triviales"
    ]
    
    # Termes de remplacement suggérés
    REPLACEMENT_SUGGESTIONS = {
        "meilleur": "amélioré",
        "optimal": "optimisé",
        "idéal": "adapté",
        "parfait": "approprié",
        "excellent": "efficace",
        "simple": "de conception simple",
        "facile": "aisé",
        "évident": "apparent"
    }
    
    def validate_keywords(
        self, 
        text: str, 
        section: PatentSection
    ) -> ValidationResult:
        """
        Valide la présence des mots-clés obligatoires dans une section.
        
        Args:
            text: Texte à valider
            section: Section du brevet
            
        Returns:
            Résultat de validation avec mots-clés manquants
        """
        text_lower = text.lower()
        required = self.REQUIRED_KEYWORDS.get(section, [])
        
        found = []
        missing = []
        
        for keyword in required:
            if keyword in text_lower:
                found.append(keyword)
            else:
                missing.append(keyword)
        
        issues = []
        suggestions = []
        
        if missing:
            issues.append(f"Mots-clés obligatoires manquants: {', '.join(missing)}")
            suggestions.append(
                f"Ajouter les mots-clés obligatoires pour {section.value}: {', '.join(missing)}"
            )
        
        # Vérifier les mots-clés recommandés
        recommended = self.RECOMMENDED_KEYWORDS.get(section, [])
        missing_recommended = [kw for kw in recommended if kw not in text_lower]
        
        if missing_recommended and section != PatentSection.ABSTRACT:
            suggestions.append(
                f"Considérer l'ajout de: {', '.join(missing_recommended[:2])}"
            )
        
        is_valid = len(missing) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            missing_keywords=missing,
            found_keywords=found,
            issues=issues,
            suggestions=suggestions
        )
    
    def find_non_technical_adjectives(self, text: str) -> List[Tuple[str, int]]:
        """
        Trouve tous les adjectifs non-techniques dans le texte.
        
        Args:
            text: Texte à analyser
            
        Returns:
            Liste de tuples (adjectif, position)
        """
        found = []
        text_lower = text.lower()
        
        for adj in self.NON_TECHNICAL_ADJECTIVES:
            # Recherche avec word boundaries pour éviter faux positifs
            pattern = r'\b' + re.escape(adj) + r'\b'
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            
            for match in matches:
                found.append((match.group(), match.start()))
        
        return found
    
    def remove_non_technical_adjectives(
        self, 
        text: str, 
        auto_replace: bool = True
    ) -> Tuple[str, List[str]]:
        """
        Supprime ou remplace les adjectifs non-techniques.
        
        Args:
            text: Texte à nettoyer
            auto_replace: Si True, remplace par suggestions; sinon supprime
            
        Returns:
            Tuple (texte nettoyé, liste des modifications)
        """
        modifications = []
        cleaned_text = text
        
        for adj in self.NON_TECHNICAL_ADJECTIVES:
            pattern = r'\b' + re.escape(adj) + r'\b'
            
            if re.search(pattern, cleaned_text, re.IGNORECASE):
                if auto_replace and adj in self.REPLACEMENT_SUGGESTIONS:
                    replacement = self.REPLACEMENT_SUGGESTIONS[adj]
                    cleaned_text = re.sub(
                        pattern, 
                        replacement, 
                        cleaned_text, 
                        flags=re.IGNORECASE
                    )
                    modifications.append(f"Remplacé '{adj}' par '{replacement}'")
                else:
                    # Suppression avec nettoyage des espaces multiples
                    cleaned_text = re.sub(
                        pattern + r'\s*', 
                        '', 
                        cleaned_text, 
                        flags=re.IGNORECASE
                    )
                    modifications.append(f"Supprimé '{adj}'")
        
        # Nettoyer les espaces multiples
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
        cleaned_text = cleaned_text.strip()
        
        return cleaned_text, modifications
    
    def validate_claims_structure(self, claims_text: str) -> ValidationResult:
        """
        Valide la structure des revendications.
        
        Args:
            claims_text: Texte des revendications
            
        Returns:
            Résultat de validation de structure
        """
        issues = []
        suggestions = []
        
        # Vérifier numérotation
        claim_numbers = re.findall(r'^\s*(\d+)\.\s', claims_text, re.MULTILINE)
        
        if not claim_numbers:
            issues.append("Aucune revendication numérotée trouvée")
            suggestions.append("Numéroter les revendications: 1., 2., 3., ...")
        else:
            # Vérifier séquence
            numbers = [int(n) for n in claim_numbers]
            if numbers != list(range(1, len(numbers) + 1)):
                issues.append("Numérotation non-séquentielle des revendications")
                suggestions.append("Assurer numérotation séquentielle: 1, 2, 3...")
        
        # Vérifier "caractérisé en ce que" dans première revendication
        first_claim_match = re.search(r'1\.\s*(.+?)(?=\n\d+\.|$)', claims_text, re.DOTALL)
        if first_claim_match:
            first_claim = first_claim_match.group(1)
            if "caractérisé en ce que" not in first_claim.lower():
                issues.append("Revendication 1 manque 'caractérisé en ce que'")
                suggestions.append("Ajouter 'caractérisé en ce que' dans revendication indépendante")
        
        # Vérifier références dans revendications dépendantes
        dependent_claims = re.findall(
            r'(\d+)\.\s*[^.]*(?:selon|revendication)\s+(?:la\s+)?revendication\s+(\d+)',
            claims_text,
            re.IGNORECASE
        )
        
        for claim_num, ref_num in dependent_claims:
            if int(ref_num) >= int(claim_num):
                issues.append(
                    f"Revendication {claim_num} référence revendication {ref_num} (postérieure)"
                )
                suggestions.append("Revendications dépendantes doivent référencer revendications antérieures")
        
        is_valid = len(issues) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            missing_keywords=[],
            found_keywords=[],
            issues=issues,
            suggestions=suggestions
        )
    
    def check_abstract_length(self, abstract: str) -> ValidationResult:
        """
        Vérifie que l'abrégé respecte la limite de 150 mots.
        
        Args:
            abstract: Texte de l'abrégé
            
        Returns:
            Résultat de validation
        """
        # Compter les mots (séparés par espaces)
        words = abstract.split()
        word_count = len(words)
        
        issues = []
        suggestions = []
        
        if word_count > 150:
            issues.append(f"Abrégé trop long: {word_count} mots (max 150)")
            suggestions.append(f"Réduire de {word_count - 150} mots")
        elif word_count == 0:
            issues.append("Abrégé vide")
            suggestions.append("Ajouter un abrégé de 100-150 mots")
        
        is_valid = 0 < word_count <= 150
        
        return ValidationResult(
            is_valid=is_valid,
            missing_keywords=[],
            found_keywords=[],
            issues=issues,
            suggestions=suggestions
        )
    
    def validate_inpi_format(self, description: str) -> ValidationResult:
        """
        Valide le format INPI avec numérotation [0001], [0002]...
        
        Args:
            description: Texte de la description
            
        Returns:
            Résultat de validation
        """
        issues = []
        suggestions = []
        
        # Chercher les paragraphes numérotés [XXXX]
        paragraph_numbers = re.findall(r'\[(\d+)\]', description)
        
        if not paragraph_numbers:
            issues.append("Format INPI manquant: pas de numérotation [0001]")
            suggestions.append("Ajouter numérotation [0001], [0002]... au début de chaque paragraphe")
        else:
            # Vérifier format avec zéros initiaux
            for num_str in paragraph_numbers:
                if len(num_str) != 4:
                    issues.append(f"Numéro mal formaté: [{num_str}] (doit être [0001])")
                    suggestions.append("Utiliser format [0001], [0002], [0003]...")
                    break
            
            # Vérifier séquence
            numbers = [int(n) for n in paragraph_numbers]
            expected = list(range(1, len(numbers) + 1))
            if numbers != expected:
                issues.append("Numérotation paragraphes non-séquentielle")
                suggestions.append("Numérotation doit être continue: [0001], [0002], [0003]...")
        
        is_valid = len(issues) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            missing_keywords=[],
            found_keywords=[],
            issues=issues,
            suggestions=suggestions
        )
    
    def calculate_quality_score(
        self,
        title: str,
        abstract: str,
        description: str,
        claims: str
    ) -> QualityScore:
        """
        Calcule un score de qualité global pour le document.
        
        Args:
            title: Titre
            abstract: Abrégé
            description: Description
            claims: Revendications
            
        Returns:
            Score de qualité détaillé
        """
        scores = {}
        
        # 1. Score mots-clés (30%)
        keyword_score = 0
        keyword_details = {}
        
        # Vérifier abstract
        abstract_val = self.validate_keywords(abstract, PatentSection.ABSTRACT)
        abstract_kw_score = (
            100 if abstract_val.is_valid 
            else (len(abstract_val.found_keywords) / max(1, len(self.REQUIRED_KEYWORDS[PatentSection.ABSTRACT]))) * 100
        )
        keyword_details['abstract'] = abstract_kw_score
        
        # Vérifier description
        desc_val = self.validate_keywords(description, PatentSection.DESCRIPTION)
        desc_kw_score = (
            100 if desc_val.is_valid
            else (len(desc_val.found_keywords) / max(1, len(self.REQUIRED_KEYWORDS[PatentSection.DESCRIPTION]))) * 100
        )
        keyword_details['description'] = desc_kw_score
        
        # Vérifier claims
        claims_val = self.validate_keywords(claims, PatentSection.CLAIMS)
        claims_kw_score = (
            100 if claims_val.is_valid
            else (len(claims_val.found_keywords) / max(1, len(self.REQUIRED_KEYWORDS[PatentSection.CLAIMS]))) * 100
        )
        keyword_details['claims'] = claims_kw_score
        
        keyword_score = int((abstract_kw_score + desc_kw_score + claims_kw_score) / 3)
        scores['keyword_score'] = keyword_score
        
        # 2. Score langage (20%)
        language_score = 100
        language_details = {}
        
        # Pénalité pour adjectifs non-techniques
        full_text = f"{title} {abstract} {description} {claims}"
        non_tech_adjs = self.find_non_technical_adjectives(full_text)
        adj_penalty = min(len(non_tech_adjs) * 5, 50)  # Max -50 points
        language_score -= adj_penalty
        language_details['non_technical_adjectives_found'] = len(non_tech_adjs)
        language_details['penalty'] = adj_penalty
        
        scores['language_score'] = max(0, language_score)
        
        # 3. Score structure (25%)
        structure_score = 100
        structure_details = {}
        
        # Vérifier longueur abrégé
        abstract_check = self.check_abstract_length(abstract)
        if not abstract_check.is_valid:
            structure_score -= 20
            structure_details['abstract_valid'] = False
        else:
            structure_details['abstract_valid'] = True
        
        # Vérifier structure revendications
        claims_structure = self.validate_claims_structure(claims)
        if not claims_structure.is_valid:
            structure_score -= min(len(claims_structure.issues) * 10, 30)
            structure_details['claims_issues'] = len(claims_structure.issues)
        else:
            structure_details['claims_valid'] = True
        
        scores['structure_score'] = max(0, structure_score)
        
        # 4. Score clarté technique (25%)
        technical_clarity_score = 100
        technical_details = {}
        
        # Vérifier présence de numéros de référence
        ref_numbers = re.findall(r'\((\d+)\)', description)
        if len(ref_numbers) < 3:
            technical_clarity_score -= 20
            technical_details['few_references'] = True
        else:
            technical_details['reference_count'] = len(ref_numbers)
        
        # Vérifier longueur minimum des sections
        if len(description.split()) < 100:
            technical_clarity_score -= 30
            technical_details['description_too_short'] = True
        
        if len(claims.split()) < 50:
            technical_clarity_score -= 20
            technical_details['claims_too_short'] = True
        
        scores['technical_clarity_score'] = max(0, technical_clarity_score)
        
        # Score global pondéré
        overall_score = int(
            keyword_score * 0.30 +
            scores['language_score'] * 0.20 +
            scores['structure_score'] * 0.25 +
            scores['technical_clarity_score'] * 0.25
        )
        
        return QualityScore(
            overall_score=overall_score,
            keyword_score=keyword_score,
            language_score=scores['language_score'],
            structure_score=scores['structure_score'],
            technical_clarity_score=scores['technical_clarity_score'],
            details={
                'keyword_details': keyword_details,
                'language_details': language_details,
                'structure_details': structure_details,
                'technical_details': technical_details
            }
        )
    
    def lint_document(
        self,
        title: str,
        abstract: str,
        description: str,
        claims: str,
        auto_fix: bool = True
    ) -> Dict:
        """
        Analyse complète et amélioration d'un document de brevet.
        
        Args:
            title: Titre
            abstract: Abrégé
            description: Description
            claims: Revendications
            auto_fix: Si True, applique corrections automatiques
            
        Returns:
            Dictionnaire avec document corrigé et métadonnées
        """
        result = {
            'original': {
                'title': title,
                'abstract': abstract,
                'description': description,
                'claims': claims
            },
            'linted': {},
            'modifications': [],
            'validations': {},
            'quality_score': None
        }
        
        # Nettoyer les adjectifs non-techniques si auto_fix
        if auto_fix:
            clean_title, title_mods = self.remove_non_technical_adjectives(title)
            clean_abstract, abstract_mods = self.remove_non_technical_adjectives(abstract)
            clean_desc, desc_mods = self.remove_non_technical_adjectives(description)
            clean_claims, claims_mods = self.remove_non_technical_adjectives(claims)
            
            result['linted'] = {
                'title': clean_title,
                'abstract': clean_abstract,
                'description': clean_desc,
                'claims': clean_claims
            }
            
            result['modifications'] = (
                title_mods + abstract_mods + desc_mods + claims_mods
            )
        else:
            result['linted'] = result['original'].copy()
        
        # Validations
        result['validations'] = {
            'abstract_keywords': self.validate_keywords(
                result['linted']['abstract'], 
                PatentSection.ABSTRACT
            ),
            'description_keywords': self.validate_keywords(
                result['linted']['description'],
                PatentSection.DESCRIPTION
            ),
            'claims_keywords': self.validate_keywords(
                result['linted']['claims'],
                PatentSection.CLAIMS
            ),
            'claims_structure': self.validate_claims_structure(
                result['linted']['claims']
            ),
            'abstract_length': self.check_abstract_length(
                result['linted']['abstract']
            )
        }
        
        # Score de qualité
        result['quality_score'] = self.calculate_quality_score(
            result['linted']['title'],
            result['linted']['abstract'],
            result['linted']['description'],
            result['linted']['claims']
        )
        
        logger.info(
            f"Document linted. Quality score: {result['quality_score'].overall_score}/100"
        )
        
        return result


# Instance globale
patent_linter = PatentTextLinter()
