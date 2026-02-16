"""
Service de calcul des annuités INPI.
Tarifs officiels 2024 sur 20 ans.
"""

import logging
from typing import List, Dict
from datetime import date, timedelta
from uuid import UUID
import calendar
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.project import Project

logger = logging.getLogger(__name__)


# Tarifs officiels INPI 2024 (en euros)
INPI_ANNUITY_RATES = {
    1: 38,
    2: 38,
    3: 38,
    4: 38,
    5: 38,
    6: 90,
    7: 120,
    8: 160,
    9: 200,
    10: 260,
    11: 370,
    12: 485,
    13: 610,
    14: 735,
    15: 860,
    16: 985,
    17: 1110,
    18: 1235,
    19: 1360,
    20: 1485
}


class INPIAnnuityCalculator:
    """
    Calculateur d'annuités INPI pour brevets français.
    """
    
    def __init__(self):
        """Initialize calculator."""
        logger.info("INPI Annuity Calculator initialized")
    
    def calculate_annuity_schedule(
        self,
        filing_date: date,
        include_late_fees: bool = False
    ) -> List[Dict]:
        """
        Calcule le calendrier complet des annuités.
        
        Args:
            filing_date: Date de dépôt du brevet
            include_late_fees: Inclure pénalités de retard
            
        Returns:
            Liste de 20 annuités avec dates et montants
        """
        schedule = []
        
        for year in range(1, 21):
            # Due date: last day of month, year after filing
            # Example: filed on 2024-03-15, year 1 due on 2025-03-31
            due_year = filing_date.year + year
            due_month = filing_date.month
            
            # Get last day of month
            last_day = calendar.monthrange(due_year, due_month)[1]
            due_date = date(due_year, due_month, last_day)
            
            amount = INPI_ANNUITY_RATES[year]
            
            # Late fees (6 months grace period with 50% surcharge)
            late_fee = 0
            grace_deadline = None
            if include_late_fees:
                late_fee = int(amount * 0.5)  # 50% surcharge
                # Grace period ends 6 months after due date
                grace_deadline = due_date + timedelta(days=180)
            
            schedule.append({
                'year': year,
                'due_date': due_date.isoformat(),
                'amount': amount,
                'late_fee': late_fee,
                'total_with_late_fee': amount + late_fee,
                'grace_deadline': grace_deadline.isoformat() if grace_deadline else None,
                'status': 'upcoming'  # or 'paid', 'overdue', 'late'
            })
        
        return schedule
    
    def calculate_total_costs(
        self,
        years: int = 20,
        discount_rate: float = None
    ) -> Dict:
        """
        Calcule le coût total sur N années.
        
        Args:
            years: Nombre d'années (1-20)
            discount_rate: Taux d'actualisation (pour NPV)
            
        Returns:
            Dict avec coûts totaux et cumulatifs
        """
        if years < 1 or years > 20:
            raise ValueError("Years must be between 1 and 20")
        
        if discount_rate is None:
            discount_rate = settings.INPI_DISCOUNT_RATE
        
        # Total nominal
        total_nominal = sum(
            INPI_ANNUITY_RATES[y]
            for y in range(1, years + 1)
        )
        
        # Net present value (valeur actuelle nette)
        total_npv = sum(
            INPI_ANNUITY_RATES[y] / ((1 + discount_rate) ** y)
            for y in range(1, years + 1)
        )
        
        # Cumulative costs
        cumulative = []
        running_total = 0
        for y in range(1, years + 1):
            running_total += INPI_ANNUITY_RATES[y]
            cumulative.append({
                'year': y,
                'annual_cost': INPI_ANNUITY_RATES[y],
                'cumulative_cost': running_total
            })
        
        return {
            'total_nominal': total_nominal,
            'total_npv': round(total_npv, 2),
            'years': years,
            'discount_rate': discount_rate,
            'cumulative': cumulative,
            'average_per_year': round(total_nominal / years, 2),
            'min_annual': min(INPI_ANNUITY_RATES[y] for y in range(1, years + 1)),
            'max_annual': max(INPI_ANNUITY_RATES[y] for y in range(1, years + 1))
        }
    
    async def get_upcoming_payments(
        self,
        project_id: UUID,
        months_ahead: int,
        db: AsyncSession
    ) -> List[Dict]:
        """
        Retourne les paiements à venir dans les N prochains mois.
        
        Args:
            project_id: ID du projet
            months_ahead: Nombre de mois à l'avance
            db: Database session
            
        Returns:
            Liste des paiements à venir
        """
        # Get project
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        
        if not project or not project.filing_date:
            return []
        
        # Calculate full schedule
        schedule = self.calculate_annuity_schedule(
            filing_date=project.filing_date,
            include_late_fees=False
        )
        
        # Filter upcoming payments
        today = date.today()
        deadline = today + timedelta(days=months_ahead * 30)
        
        upcoming = [
            payment for payment in schedule
            if today <= date.fromisoformat(payment['due_date']) <= deadline
            and payment['status'] == 'upcoming'
        ]
        
        return upcoming
    
    def get_payment_for_year(
        self,
        filing_date: date,
        year: int
    ) -> Dict:
        """
        Retourne les détails d'un paiement pour une année spécifique.
        
        Args:
            filing_date: Date de dépôt
            year: Année (1-20)
            
        Returns:
            Dict avec détails du paiement
        """
        if year < 1 or year > 20:
            raise ValueError("Year must be between 1 and 20")
        
        schedule = self.calculate_annuity_schedule(filing_date)
        return schedule[year - 1]  # Index 0-based
    
    def calculate_years_to_breakeven(
        self,
        initial_cost: float,
        annual_revenue: float
    ) -> int:
        """
        Calcule le nombre d'années pour rentabiliser le brevet.
        
        Args:
            initial_cost: Coût initial (dépôt + rédaction)
            annual_revenue: Revenu annuel estimé
            
        Returns:
            Nombre d'années pour breakeven
        """
        cumulative_cost = initial_cost
        cumulative_revenue = 0
        
        for year in range(1, 21):
            cumulative_cost += INPI_ANNUITY_RATES[year]
            cumulative_revenue += annual_revenue
            
            if cumulative_revenue >= cumulative_cost:
                return year
        
        return 20  # Beyond 20 years
    
    def get_rates_table(self) -> List[Dict]:
        """
        Retourne le tableau complet des tarifs INPI.
        """
        return [
            {'year': year, 'amount': amount}
            for year, amount in INPI_ANNUITY_RATES.items()
        ]


# Instance globale
inpi_calculator = INPIAnnuityCalculator()
