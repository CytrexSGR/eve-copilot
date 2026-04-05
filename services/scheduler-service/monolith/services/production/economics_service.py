"""
Production Economics Service

Business logic for cost calculations, profitability analysis, and ROI.
"""

from decimal import Decimal
from typing import Dict, List, Any, Optional
from services.production.economics_repository import ProductionEconomicsRepository
from services.production.chain_repository import ProductionChainRepository
from src.database import get_db_connection
from src.services.production.tax_models import TaxProfile, FacilityProfile, SystemCostIndex
from src.services.production.tax_repository import TaxRepository, FacilityRepository, SystemCostIndexRepository


class ProductionEconomicsService:
    """Service for production economics operations"""

    def __init__(self):
        self.repo = ProductionEconomicsRepository()
        self.chain_repo = ProductionChainRepository()

    def get_economics(
        self,
        type_id: int,
        region_id: int,
        me: int = 0,
        te: int = 0,
        tax_profile_id: Optional[int] = None,
        facility_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get complete economics analysis for an item

        Args:
            type_id: Item type ID
            region_id: Region ID
            me: Material Efficiency (0-10)
            te: Time Efficiency (0-20)
            tax_profile_id: Optional tax profile ID for broker/sales tax
            facility_id: Optional facility profile ID for ME/TE/cost bonuses

        Returns:
            Complete economics data with adjusted costs
        """
        # Get base economics
        economics = self.repo.get(type_id, region_id)

        if not economics:
            return {'error': 'Economics data not found', 'type_id': type_id, 'region_id': region_id}

        # Get item info
        item_info = self._get_item_info(type_id)
        region_name = self._get_region_name(region_id)

        # Load tax profile if provided
        tax_profile = None
        if tax_profile_id is not None:
            tax_profile = self._load_tax_profile(tax_profile_id)

        # Load facility profile if provided
        facility = None
        system_cost_index = None
        if facility_id is not None:
            facility = self._load_facility_profile(facility_id)
            if facility:
                system_cost_index = self._load_system_cost_index(facility['system_id'])

        # Calculate material cost with combined ME (blueprint + facility bonus)
        base_material_cost = economics['material_cost']
        final_me = me
        if facility and facility.get('me_bonus'):
            final_me = me + float(facility['me_bonus'])
        adjusted_material_cost = base_material_cost * (1 - final_me / 100)

        # Apply TE to production time (blueprint + facility bonus)
        base_time = economics['base_production_time']
        final_te = te
        if facility and facility.get('te_bonus'):
            final_te = te + float(facility['te_bonus'])
        adjusted_time = int(base_time * (1 - final_te / 100))

        # Calculate job cost with system cost index
        base_job_cost = economics['base_job_cost']
        if system_cost_index:
            manufacturing_index = float(system_cost_index.get('manufacturing_index', 0))
            adjusted_job_cost = base_job_cost * (1 + manufacturing_index)
        else:
            adjusted_job_cost = base_job_cost

        # Calculate broker fees and sales tax
        broker_fee = 0.0
        sales_tax = 0.0
        if tax_profile:
            sell_price = economics['market_sell_price'] or 0
            broker_fee_rate = float(tax_profile.get('broker_fee_sell', 0))
            sales_tax_rate = float(tax_profile.get('sales_tax', 0))
            broker_fee = sell_price * (broker_fee_rate / 100)
            sales_tax = sell_price * (sales_tax_rate / 100)

        total_cost = adjusted_material_cost + adjusted_job_cost

        # Calculate profit and ROI
        profit_sell = None
        profit_buy = None
        roi_sell = None
        roi_buy = None

        if economics['market_sell_price']:
            # Net revenue = sell price - broker fee - sales tax
            net_revenue = economics['market_sell_price'] - broker_fee - sales_tax
            profit_sell = net_revenue - total_cost
            roi_sell = (profit_sell / total_cost * 100) if total_cost > 0 else 0

        if economics['market_buy_price']:
            profit_buy = economics['market_buy_price'] - total_cost
            roi_buy = (profit_buy / total_cost * 100) if total_cost > 0 else 0

        return {
            'type_id': type_id,
            'item_name': item_info['name'] if item_info else 'Unknown',
            'region_id': region_id,
            'region_name': region_name,
            'me_level': me,
            'te_level': te,
            'costs': {
                'material_cost': adjusted_material_cost,
                'job_cost': adjusted_job_cost,
                'broker_fee': broker_fee,
                'sales_tax': sales_tax,
                'total_cost': total_cost
            },
            'market': {
                'sell_price': economics['market_sell_price'],
                'buy_price': economics['market_buy_price'],
                'daily_volume': 0  # TODO: Add when available
            },
            'profitability': {
                'profit_sell': profit_sell,
                'profit_buy': profit_buy,
                'roi_sell_percent': roi_sell,
                'roi_buy_percent': roi_buy
            },
            'production_time': adjusted_time,
            'updated_at': economics['updated_at'],
            'tax_profile': tax_profile,
            'facility': facility
        }

    def find_opportunities(
        self,
        region_id: int,
        min_roi: float = 0,
        min_profit: float = 0,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Find profitable manufacturing opportunities

        Args:
            region_id: Region to search in
            min_roi: Minimum ROI percentage
            min_profit: Minimum profit in ISK
            limit: Max results

        Returns:
            List of opportunities
        """
        opportunities = self.repo.find_opportunities(
            region_id=region_id,
            min_roi=min_roi,
            min_profit=min_profit,
            limit=limit
        )

        return {
            'region_id': region_id,
            'region_name': self._get_region_name(region_id),
            'filters': {
                'min_roi': min_roi,
                'min_profit': min_profit
            },
            'opportunities': opportunities,
            'total_count': len(opportunities)
        }

    def compare_regions(self, type_id: int) -> Dict[str, Any]:
        """
        Compare production economics across multiple regions

        Args:
            type_id: Item type ID

        Returns:
            Multi-region comparison
        """
        # Get data for major regions
        regions = [
            (10000002, 'The Forge'),
            (10000043, 'Domain'),
            (10000030, 'Heimatar'),
            (10000032, 'Sinq Laison'),
            (10000042, 'Metropolis')
        ]

        item_info = self._get_item_info(type_id)
        results = []
        best_region = None
        best_roi = -999999

        for region_id, region_name in regions:
            economics = self.repo.get(type_id, region_id)

            if economics and economics['market_sell_price']:
                roi = economics['roi_sell_percent']
                profit = economics['profit_sell']

                results.append({
                    'region_id': region_id,
                    'region_name': region_name,
                    'roi_percent': roi,
                    'profit': profit,
                    'total_cost': economics['total_cost'],
                    'market_price': economics['market_sell_price']
                })

                if roi > best_roi:
                    best_roi = roi
                    best_region = {
                        'region_id': region_id,
                        'region_name': region_name,
                        'roi_percent': roi,
                        'profit': profit
                    }

        return {
            'type_id': type_id,
            'item_name': item_info['name'] if item_info else 'Unknown',
            'regions': sorted(results, key=lambda x: x['roi_percent'], reverse=True),
            'best_region': best_region,
            'total_regions': len(results)
        }

    def _get_item_info(self, type_id: int) -> Optional[Dict[str, Any]]:
        """Get item name and basic info"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT "typeID", "typeName"
                        FROM "invTypes"
                        WHERE "typeID" = %s
                    """, (type_id,))

                    row = cursor.fetchone()
                    if not row:
                        return None

                    return {'type_id': row[0], 'name': row[1]}
        except Exception as e:
            print(f"Error getting item info: {e}")
            return None

    def _get_region_name(self, region_id: int) -> str:
        """Get region name"""
        region_names = {
            10000002: 'The Forge',
            10000043: 'Domain',
            10000030: 'Heimatar',
            10000032: 'Sinq Laison',
            10000042: 'Metropolis'
        }
        return region_names.get(region_id, f'Region {region_id}')

    def _load_tax_profile(self, tax_profile_id: int) -> Optional[Dict[str, Any]]:
        """Load tax profile by ID.

        Args:
            tax_profile_id: Tax profile ID to load

        Returns:
            Tax profile data as dict or None if not found
        """
        try:
            with get_db_connection() as conn:
                tax_repo = TaxRepository(conn)
                profile = tax_repo.get_by_id(tax_profile_id)
                if profile:
                    return {
                        'id': profile.id,
                        'name': profile.name,
                        'broker_fee_buy': float(profile.broker_fee_buy),
                        'broker_fee_sell': float(profile.broker_fee_sell),
                        'sales_tax': float(profile.sales_tax),
                        'is_default': profile.is_default
                    }
                return None
        except Exception as e:
            print(f"Error loading tax profile: {e}")
            return None

    def _load_facility_profile(self, facility_id: int) -> Optional[Dict[str, Any]]:
        """Load facility profile by ID.

        Args:
            facility_id: Facility profile ID to load

        Returns:
            Facility profile data as dict or None if not found
        """
        try:
            with get_db_connection() as conn:
                facility_repo = FacilityRepository(conn)
                profile = facility_repo.get_by_id(facility_id)
                if profile:
                    return {
                        'id': profile.id,
                        'name': profile.name,
                        'system_id': profile.system_id,
                        'system_name': profile.system_name,
                        'structure_type': profile.structure_type,
                        'me_bonus': float(profile.me_bonus),
                        'te_bonus': float(profile.te_bonus),
                        'cost_bonus': float(profile.cost_bonus),
                        'facility_tax': float(profile.facility_tax)
                    }
                return None
        except Exception as e:
            print(f"Error loading facility profile: {e}")
            return None

    def _load_system_cost_index(self, system_id: int) -> Optional[Dict[str, Any]]:
        """Load system cost index for a solar system.

        Args:
            system_id: Solar system ID

        Returns:
            System cost index data as dict or None if not found
        """
        try:
            with get_db_connection() as conn:
                sci_repo = SystemCostIndexRepository(conn)
                sci = sci_repo.get_by_system(system_id)
                if sci:
                    return {
                        'system_id': sci.system_id,
                        'system_name': sci.system_name,
                        'manufacturing_index': float(sci.manufacturing_index),
                        'reaction_index': float(sci.reaction_index),
                        'copying_index': float(sci.copying_index),
                        'invention_index': float(sci.invention_index)
                    }
                return None
        except Exception as e:
            print(f"Error loading system cost index: {e}")
            return None
