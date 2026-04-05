"""Character service business logic."""
import logging
from typing import Optional, List


from app.config import settings
from collections import defaultdict
from app.models import (
    WalletBalance, AssetList, Asset, SkillData, Skill,
    SkillQueue, SkillQueueItem, MarketOrderList, MarketOrder,
    IndustryJobList, IndustryJob, BlueprintList, Blueprint,
    CharacterInfo, CharacterLocation, CharacterShip,
    CharacterAttributes, CharacterImplants, Implant,
    WalletJournal, WalletJournalEntry,
    WalletTransactions, WalletTransaction,
    CorporationInfo, CorporationWallet, CorporationWalletDivision,
    CorpMarketOrderList, CorpMarketOrder,
    CorpTransactions, CorpTransaction,
    ValuedAsset, LocationSummary, ValuedAssetList,
)
from app.services.esi_client import ESIClient
from app.services.repository import CharacterRepository
from app.services.auth_client import AuthClient

logger = logging.getLogger(__name__)


class CharacterService:
    """Business logic for character data."""

    def __init__(self, db, redis=None):
        self.db = db
        self.redis = redis
        self.repo = CharacterRepository(db, redis)
        self.esi = ESIClient()
        self.auth_client = AuthClient()

    def _get_token(self, character_id: int) -> Optional[str]:
        """Get access token for character from auth-service, with auto-refresh."""
        token = self.auth_client.get_valid_token(character_id)
        if not token:
            logger.info(f"Token unavailable for {character_id}, attempting refresh")
            if self.auth_client.refresh_token(character_id):
                token = self.auth_client.get_valid_token(character_id)
                if token:
                    logger.info(f"Token refresh successful for {character_id}")
                else:
                    logger.warning(f"Token still unavailable after refresh for {character_id}")
            else:
                logger.warning(f"Token refresh failed for {character_id}")
        return token

    # Character data methods

    def get_wallet(self, character_id: int) -> Optional[WalletBalance]:
        """Get character wallet balance."""
        token = self._get_token(character_id)
        if not token:
            return None

        balance = self.esi.get_wallet(character_id, token)
        if balance is None:
            return None

        return WalletBalance(character_id=character_id, balance=balance)

    def get_assets(
        self,
        character_id: int,
        location_id: Optional[int] = None
    ) -> Optional[AssetList]:
        """Get character assets."""
        token = self._get_token(character_id)
        if not token:
            return None

        # Fetch all pages
        all_assets = []
        page = 1
        while True:
            assets = self.esi.get_assets(character_id, token, page)
            if not assets:
                break
            all_assets.extend(assets)
            if len(assets) < 1000:
                break
            page += 1

        # Filter by location if specified
        if location_id:
            all_assets = [a for a in all_assets if a.get("location_id") == location_id]

        # Resolve type info
        type_ids = list(set(a.get("type_id") for a in all_assets if a.get("type_id")))
        type_info = self.repo.resolve_type_info(type_ids)

        # Resolve location names
        location_ids = list(set(a.get("location_id") for a in all_assets if a.get("location_id")))
        location_names = self.repo.resolve_location_names(location_ids)

        # Build enriched assets
        assets = []
        for a in all_assets:
            info = type_info.get(a.get("type_id"), {})
            loc_id = a.get("location_id")
            assets.append(Asset(
                item_id=a.get("item_id"),
                type_id=a.get("type_id"),
                type_name=info.get("type_name", "Unknown"),
                group_id=info.get("group_id", 0),
                group_name=info.get("group_name", "Unknown"),
                category_id=info.get("category_id", 0),
                category_name=info.get("category_name", "Unknown"),
                location_id=loc_id,
                location_name=location_names.get(loc_id, "Unknown"),
                quantity=a.get("quantity", 1),
                is_singleton=a.get("is_singleton", False),
                location_flag=a.get("location_flag"),
                location_type=a.get("location_type")
            ))

        return AssetList(
            character_id=character_id,
            total_items=len(assets),
            assets=assets
        )

    def _get_adjusted_prices(self) -> dict[int, float]:
        """Fetch ESI adjusted prices (no auth needed)."""
        import httpx
        try:
            resp = httpx.get(
                f"{settings.esi_base_url}/markets/prices/",
                params={"datasource": "tranquility"},
                timeout=30,
            )
            if resp.status_code == 200:
                return {
                    p["type_id"]: p.get("adjusted_price", p.get("average_price", 0))
                    for p in resp.json()
                }
        except Exception as e:
            logger.warning(f"Failed to fetch ESI prices: {e}")
        return {}

    def get_valued_assets(
        self,
        character_id: int,
        location_id: Optional[int] = None,
    ) -> Optional[ValuedAssetList]:
        """Get character assets with market valuations."""
        token = self._get_token(character_id)
        if not token:
            return None

        # Fetch all pages of assets
        all_assets = []
        page = 1
        while True:
            assets = self.esi.get_assets(character_id, token, page)
            if not assets:
                break
            all_assets.extend(assets)
            if len(assets) < 1000:
                break
            page += 1

        if location_id:
            all_assets = [a for a in all_assets if a.get("location_id") == location_id]

        # Reparent items inside ships/containers to their parent's real location
        item_map = {a["item_id"]: a for a in all_assets if "item_id" in a}
        for a in all_assets:
            if a.get("location_type") == "item":
                parent_id = a.get("location_id")
                # Walk up the chain (ship in station, item in ship)
                seen = set()
                while parent_id in item_map and parent_id not in seen:
                    seen.add(parent_id)
                    parent = item_map[parent_id]
                    parent_id = parent.get("location_id")
                a["_real_location_id"] = parent_id

        # Resolve type info with volume
        type_ids = list(set(a.get("type_id") for a in all_assets if a.get("type_id")))
        type_info = self.repo.resolve_type_info_with_volume(type_ids)

        # Resolve location names (use real locations for items inside ships)
        real_loc_ids = set()
        for a in all_assets:
            real_loc_ids.add(a.get("_real_location_id", a.get("location_id")))
        location_names = self.repo.resolve_location_names(list(real_loc_ids))

        # Fetch ESI adjusted prices
        prices = self._get_adjusted_prices()

        # Build valued assets
        valued_assets = []
        total_value = 0.0
        total_volume = 0.0
        loc_stats: dict[int, dict] = defaultdict(lambda: {
            "value": 0.0, "volume": 0.0, "items": 0, "types": set()
        })

        for a in all_assets:
            tid = a.get("type_id")
            info = type_info.get(tid, {})
            loc_id = a.get("_real_location_id", a.get("location_id"))
            qty = a.get("quantity", 1)
            unit_price = prices.get(tid, 0.0)
            vol = info.get("volume", 0.0)
            item_value = unit_price * qty
            item_volume = vol * qty

            va = ValuedAsset(
                item_id=a.get("item_id"),
                type_id=tid,
                type_name=info.get("type_name", "Unknown"),
                group_id=info.get("group_id", 0),
                group_name=info.get("group_name", "Unknown"),
                category_id=info.get("category_id", 0),
                category_name=info.get("category_name", "Unknown"),
                location_id=loc_id,
                location_name=location_names.get(loc_id, "Unknown"),
                quantity=qty,
                is_singleton=a.get("is_singleton", False),
                location_flag=a.get("location_flag"),
                location_type=a.get("location_type"),
                unit_price=unit_price,
                total_value=item_value,
                volume=vol,
                total_volume=item_volume,
            )
            valued_assets.append(va)
            total_value += item_value
            total_volume += item_volume

            ls = loc_stats[loc_id]
            ls["value"] += item_value
            ls["volume"] += item_volume
            ls["items"] += 1
            ls["types"].add(tid)

        # Build location summaries
        location_summaries = sorted(
            [
                LocationSummary(
                    location_id=lid,
                    location_name=location_names.get(lid, "Unknown"),
                    total_value=s["value"],
                    total_volume=s["volume"],
                    item_count=s["items"],
                    type_count=len(s["types"]),
                )
                for lid, s in loc_stats.items()
            ],
            key=lambda x: x.total_value,
            reverse=True,
        )

        return ValuedAssetList(
            character_id=character_id,
            total_value=total_value,
            total_volume=total_volume,
            total_items=len(valued_assets),
            total_types=len(type_ids),
            location_summaries=location_summaries,
            assets=valued_assets,
        )

    def get_skills(self, character_id: int) -> Optional[SkillData]:
        """Get character skills."""
        token = self._get_token(character_id)
        if not token:
            return None

        result = self.esi.get_skills(character_id, token)
        if not result:
            return None

        skills_data = result.get("skills", [])
        skill_ids = [s.get("skill_id") for s in skills_data]
        skill_info = self.repo.resolve_type_info(skill_ids)

        skills = []
        for s in skills_data:
            skill_id = s.get("skill_id")
            info = skill_info.get(skill_id, {})
            skills.append(Skill(
                skill_id=skill_id,
                skill_name=info.get("type_name", "Unknown"),
                level=s.get("active_skill_level", 0),
                trained_level=s.get("trained_skill_level", 0),
                skillpoints=s.get("skillpoints_in_skill", 0),
                group_name=info.get("group_name", "Unknown"),
            ))

        skills.sort(key=lambda x: x.skill_name)

        return SkillData(
            character_id=character_id,
            total_sp=result.get("total_sp", 0),
            unallocated_sp=result.get("unallocated_sp", 0),
            skill_count=len(skills),
            skills=skills
        )

    def get_skillqueue(self, character_id: int) -> Optional[SkillQueue]:
        """Get character skill queue."""
        token = self._get_token(character_id)
        if not token:
            return None

        result = self.esi.get_skillqueue(character_id, token)
        if not result:
            return SkillQueue(character_id=character_id)

        skill_ids = [item.get("skill_id") for item in result]
        skill_info = self.repo.get_skill_info(skill_ids)

        queue_items = []
        for item in result:
            skill_id = item.get("skill_id")
            info = skill_info.get(skill_id, {"name": "Unknown", "description": ""})

            level_start_sp = item.get("level_start_sp", 0)
            level_end_sp = item.get("level_end_sp", 0)
            training_start_sp = item.get("training_start_sp", 0)
            sp_remaining = max(0, level_end_sp - training_start_sp)

            training_progress = 0.0
            if level_end_sp > level_start_sp:
                sp_trained = training_start_sp - level_start_sp
                sp_needed = level_end_sp - level_start_sp
                training_progress = min(100.0, max(0.0, (sp_trained / sp_needed) * 100))

            queue_items.append(SkillQueueItem(
                skill_id=skill_id,
                skill_name=info["name"],
                skill_description=info["description"],
                finish_date=item.get("finish_date"),
                start_date=item.get("start_date"),
                finished_level=item.get("finished_level", 0),
                queue_position=item.get("queue_position", 0),
                level_start_sp=level_start_sp,
                level_end_sp=level_end_sp,
                training_start_sp=training_start_sp,
                sp_remaining=sp_remaining,
                training_progress=training_progress
            ))

        return SkillQueue(
            character_id=character_id,
            queue_length=len(queue_items),
            queue=queue_items
        )

    def get_orders(self, character_id: int) -> Optional[MarketOrderList]:
        """Get character market orders."""
        token = self._get_token(character_id)
        if not token:
            return None

        result = self.esi.get_orders(character_id, token)

        type_ids = [o.get("type_id") for o in result]
        type_names = self.repo.resolve_type_names(type_ids)

        location_ids = [o.get("location_id") for o in result]
        location_names = self.repo.resolve_location_names(location_ids)

        orders = []
        for o in result:
            type_id = o.get("type_id")
            location_id = o.get("location_id")
            orders.append(MarketOrder(
                order_id=o.get("order_id"),
                type_id=type_id,
                type_name=type_names.get(type_id, "Unknown"),
                is_buy_order=o.get("is_buy_order", False),
                price=o.get("price", 0),
                volume_total=o.get("volume_total", 0),
                volume_remain=o.get("volume_remain", 0),
                location_id=location_id,
                location_name=location_names.get(location_id, "Unknown"),
                region_id=o.get("region_id", 0),
                issued=o.get("issued"),
                duration=o.get("duration", 0),
                min_volume=o.get("min_volume", 1),
                range=o.get("range", "station")
            ))

        buy_orders = [o for o in orders if o.is_buy_order]
        sell_orders = [o for o in orders if not o.is_buy_order]

        return MarketOrderList(
            character_id=character_id,
            total_orders=len(orders),
            buy_orders=len(buy_orders),
            sell_orders=len(sell_orders),
            orders=orders
        )

    def get_industry_jobs(
        self,
        character_id: int,
        include_completed: bool = False
    ) -> Optional[IndustryJobList]:
        """Get character industry jobs."""
        token = self._get_token(character_id)
        if not token:
            return None

        result = self.esi.get_industry_jobs(character_id, token, include_completed)

        # Resolve type names
        type_ids = []
        for job in result:
            if job.get("blueprint_type_id"):
                type_ids.append(job["blueprint_type_id"])
            if job.get("product_type_id"):
                type_ids.append(job["product_type_id"])
        type_names = self.repo.resolve_type_names(type_ids)

        jobs = []
        for j in result:
            bp_type_id = j.get("blueprint_type_id")
            product_type_id = j.get("product_type_id")
            jobs.append(IndustryJob(
                job_id=j.get("job_id"),
                activity_id=j.get("activity_id"),
                blueprint_id=j.get("blueprint_id"),
                blueprint_type_id=bp_type_id,
                blueprint_type_name=type_names.get(bp_type_id, "Unknown"),
                product_type_id=product_type_id,
                product_type_name=type_names.get(product_type_id, "Unknown") if product_type_id else "",
                status=j.get("status", ""),
                runs=j.get("runs", 1),
                licensed_runs=j.get("licensed_runs", 0),
                start_date=j.get("start_date"),
                end_date=j.get("end_date"),
                duration=j.get("duration", 0),
                station_id=j.get("station_id", 0),
                cost=j.get("cost", 0)
            ))

        active_jobs = [j for j in jobs if j.status == "active"]

        return IndustryJobList(
            character_id=character_id,
            total_jobs=len(jobs),
            active_jobs=len(active_jobs),
            jobs=jobs
        )

    def get_blueprints(self, character_id: int) -> Optional[BlueprintList]:
        """Get character blueprints."""
        token = self._get_token(character_id)
        if not token:
            return None

        # Fetch all pages
        all_blueprints = []
        page = 1
        while True:
            bps = self.esi.get_blueprints(character_id, token, page)
            if not bps:
                break
            all_blueprints.extend(bps)
            if len(bps) < 1000:
                break
            page += 1

        type_ids = [bp.get("type_id") for bp in all_blueprints]
        type_names = self.repo.resolve_type_names(type_ids)

        location_ids = [bp.get("location_id") for bp in all_blueprints]
        location_names = self.repo.resolve_location_names(location_ids)

        blueprints = []
        for bp in all_blueprints:
            type_id = bp.get("type_id")
            location_id = bp.get("location_id")
            blueprints.append(Blueprint(
                item_id=bp.get("item_id"),
                type_id=type_id,
                type_name=type_names.get(type_id, "Unknown"),
                location_id=location_id,
                location_name=location_names.get(location_id, "Unknown"),
                quantity=bp.get("quantity", -1),
                runs=bp.get("runs", -1),
                material_efficiency=bp.get("material_efficiency", 0),
                time_efficiency=bp.get("time_efficiency", 0)
            ))

        originals = [b for b in blueprints if b.quantity == -1]
        copies = [b for b in blueprints if b.quantity == -2]

        return BlueprintList(
            character_id=character_id,
            total_blueprints=len(blueprints),
            originals=len(originals),
            copies=len(copies),
            blueprints=blueprints
        )

    def _get_authoritative_corp(self, character_id: int, esi_corp_id: int) -> tuple:
        """Get authoritative corporation_id from corp history.

        ESI /characters/{id}/ can return stale corporation_id.
        Corp history endpoint is authoritative — use most recent entry.
        Returns (corporation_id, alliance_id).
        """
        try:
            history = self.esi.get_character_corporation_history(character_id)
            if history:
                latest = history[0]  # sorted by start_date desc
                real_corp_id = latest.get("corporation_id")
                if real_corp_id and real_corp_id != esi_corp_id:
                    logger.info(
                        f"ESI corp mismatch for {character_id}: "
                        f"character endpoint says {esi_corp_id}, "
                        f"corp history says {real_corp_id} — using corp history"
                    )
                    corp_info = self.esi.get_corporation_info(real_corp_id)
                    alliance_id = corp_info.get("alliance_id") if corp_info else None
                    return real_corp_id, alliance_id
        except Exception as e:
            logger.warning(f"Corp history lookup failed for {character_id}: {e}")
        return esi_corp_id, None

    def get_character_info(self, character_id: int) -> Optional[CharacterInfo]:
        """Get public character information."""
        result = self.esi.get_character_info(character_id)
        if not result:
            return None

        esi_corp_id = result.get("corporation_id", 0)
        corp_id, hist_alliance_id = self._get_authoritative_corp(
            character_id, esi_corp_id
        )
        alliance_id = hist_alliance_id if corp_id != esi_corp_id else result.get("alliance_id")

        return CharacterInfo(
            character_id=character_id,
            name=result.get("name", ""),
            corporation_id=corp_id,
            alliance_id=alliance_id,
            birthday=result.get("birthday"),
            security_status=result.get("security_status", 0),
            title=result.get("title"),
            description=result.get("description")
        )

    def get_location(self, character_id: int) -> Optional[CharacterLocation]:
        """Get character location."""
        token = self._get_token(character_id)
        if not token:
            return None

        result = self.esi.get_location(character_id, token)
        if not result:
            return None

        system_id = result.get("solar_system_id", 0)
        station_id = result.get("station_id")

        system_names = self.repo.resolve_system_names([system_id])
        station_name = None
        if station_id:
            station_names = self.repo.resolve_station_names([station_id])
            station_name = station_names.get(station_id)

        return CharacterLocation(
            character_id=character_id,
            solar_system_id=system_id,
            solar_system_name=system_names.get(system_id, "Unknown"),
            station_id=station_id,
            station_name=station_name,
            structure_id=result.get("structure_id")
        )

    def get_ship(self, character_id: int) -> Optional[CharacterShip]:
        """Get character current ship."""
        token = self._get_token(character_id)
        if not token:
            return None

        result = self.esi.get_ship(character_id, token)
        if not result:
            return None

        ship_type_id = result.get("ship_type_id", 0)
        type_names = self.repo.resolve_type_names([ship_type_id])

        return CharacterShip(
            character_id=character_id,
            ship_type_id=ship_type_id,
            ship_type_name=type_names.get(ship_type_id, "Unknown"),
            ship_item_id=result.get("ship_item_id", 0),
            ship_name=result.get("ship_name", "")
        )

    def get_attributes(self, character_id: int) -> Optional[CharacterAttributes]:
        """Get character attributes."""
        token = self._get_token(character_id)
        if not token:
            return None

        result = self.esi.get_attributes(character_id, token)
        if not result:
            return None

        return CharacterAttributes(
            character_id=character_id,
            perception=result.get("perception", 20),
            memory=result.get("memory", 20),
            willpower=result.get("willpower", 20),
            intelligence=result.get("intelligence", 20),
            charisma=result.get("charisma", 19),
            bonus_remaps=result.get("bonus_remaps", 0),
            last_remap_date=result.get("last_remap_date"),
            accrued_remap_cooldown_date=result.get("accrued_remap_cooldown_date")
        )

    def get_implants(self, character_id: int) -> Optional[CharacterImplants]:
        """Get character implants."""
        token = self._get_token(character_id)
        if not token:
            return None

        implant_ids = self.esi.get_implants(character_id, token)
        if not implant_ids:
            return CharacterImplants(character_id=character_id)

        implant_info = self.repo.get_implant_info(implant_ids)

        implants = [
            Implant(
                type_id=info["type_id"],
                type_name=info["type_name"],
                slot=info.get("slot", 1),
                perception_bonus=info.get("perception_bonus", 0),
                memory_bonus=info.get("memory_bonus", 0),
                willpower_bonus=info.get("willpower_bonus", 0),
                intelligence_bonus=info.get("intelligence_bonus", 0),
                charisma_bonus=info.get("charisma_bonus", 0)
            )
            for info in implant_info
        ]

        return CharacterImplants(character_id=character_id, implants=implants)

    def get_wallet_journal(
        self,
        character_id: int,
        page: int = 1
    ) -> Optional[WalletJournal]:
        """Get character wallet journal."""
        token = self._get_token(character_id)
        if not token:
            return None

        result = self.esi.get_wallet_journal(character_id, token, page)

        entries = [
            WalletJournalEntry(
                id=e.get("id"),
                date=e.get("date"),
                ref_type=e.get("ref_type", "unknown"),
                amount=e.get("amount", 0),
                balance=e.get("balance", 0),
                description=e.get("description"),
                first_party_id=e.get("first_party_id"),
                second_party_id=e.get("second_party_id"),
                reason=e.get("reason"),
                context_id=e.get("context_id"),
                context_id_type=e.get("context_id_type")
            )
            for e in result
        ]

        return WalletJournal(
            character_id=character_id,
            entries=entries,
            total_entries=len(entries)
        )

    def get_wallet_transactions(
        self,
        character_id: int,
        from_id: Optional[int] = None
    ) -> Optional[WalletTransactions]:
        """Get character wallet transactions."""
        token = self._get_token(character_id)
        if not token:
            return None

        result = self.esi.get_wallet_transactions(character_id, token, from_id)

        type_ids = [t.get("type_id") for t in result]
        type_names = self.repo.resolve_type_names(type_ids)

        location_ids = [t.get("location_id") for t in result]
        location_names = self.repo.resolve_location_names(location_ids)

        transactions = []
        for txn in result:
            type_id = txn.get("type_id")
            location_id = txn.get("location_id")
            is_buy = txn.get("is_buy", False)
            quantity = txn.get("quantity", 0)

            transactions.append(WalletTransaction(
                transaction_id=txn.get("transaction_id"),
                date=txn.get("date"),
                type_id=type_id,
                type_name=type_names.get(type_id, "Unknown"),
                quantity=quantity if is_buy else -quantity,
                unit_price=txn.get("unit_price", 0),
                is_buy=is_buy,
                location_id=location_id,
                location_name=location_names.get(location_id, "Unknown"),
                client_id=txn.get("client_id", 0)
            ))

        return WalletTransactions(
            character_id=character_id,
            transactions=transactions,
            total_transactions=len(transactions)
        )

    # Corporation methods

    def get_corporation_id(self, character_id: int) -> Optional[int]:
        """Get corporation ID for character."""
        info = self.get_character_info(character_id)
        return info.corporation_id if info else None

    def get_corporation_info(self, corporation_id: int) -> Optional[CorporationInfo]:
        """Get corporation information."""
        result = self.esi.get_corporation_info(corporation_id)
        if not result:
            return None

        return CorporationInfo(
            corporation_id=corporation_id,
            name=result.get("name", ""),
            ticker=result.get("ticker", ""),
            member_count=result.get("member_count", 0),
            alliance_id=result.get("alliance_id"),
            ceo_id=result.get("ceo_id"),
            creator_id=result.get("creator_id"),
            date_founded=result.get("date_founded"),
            description=result.get("description"),
            home_station_id=result.get("home_station_id"),
            shares=result.get("shares", 0),
            tax_rate=result.get("tax_rate", 0),
            url=result.get("url")
        )

    def get_corporation_wallets(
        self,
        character_id: int
    ) -> Optional[CorporationWallet]:
        """Get corporation wallet balances."""
        token = self._get_token(character_id)
        if not token:
            return None

        corp_id = self.get_corporation_id(character_id)
        if not corp_id:
            return None

        corp_info = self.get_corporation_info(corp_id)
        result = self.esi.get_corporation_wallets(corp_id, token)

        divisions = [
            CorporationWalletDivision(
                division=d.get("division"),
                balance=d.get("balance", 0)
            )
            for d in result
        ]

        total_balance = sum(d.balance for d in divisions)

        return CorporationWallet(
            corporation_id=corp_id,
            corporation_name=corp_info.name if corp_info else "",
            divisions=divisions,
            total_balance=total_balance,
            formatted_total=f"{total_balance:,.2f} ISK"
        )

    def get_corporation_orders(
        self,
        character_id: int
    ) -> Optional[CorpMarketOrderList]:
        """Get corporation market orders."""
        token = self._get_token(character_id)
        if not token:
            return None

        corp_id = self.get_corporation_id(character_id)
        if not corp_id:
            return None

        result = self.esi.get_corporation_orders(corp_id, token)

        type_ids = [o.get("type_id") for o in result]
        type_names = self.repo.resolve_type_names(type_ids)

        location_ids = [o.get("location_id") for o in result]
        location_names = self.repo.resolve_location_names(location_ids)

        orders = []
        for o in result:
            type_id = o.get("type_id")
            location_id = o.get("location_id")
            orders.append(CorpMarketOrder(
                order_id=o.get("order_id"),
                type_id=type_id,
                type_name=type_names.get(type_id, "Unknown"),
                is_buy_order=o.get("is_buy_order", False),
                price=o.get("price", 0),
                volume_total=o.get("volume_total", 0),
                volume_remain=o.get("volume_remain", 0),
                location_id=location_id,
                location_name=location_names.get(location_id, "Unknown"),
                region_id=o.get("region_id", 0),
                issued=o.get("issued"),
                duration=o.get("duration", 0),
                issued_by=o.get("issued_by", 0),
                wallet_division=o.get("wallet_division", 1)
            ))

        return CorpMarketOrderList(corporation_id=corp_id, orders=orders)

    def get_corporation_transactions(
        self,
        character_id: int,
        division: int = 1,
        from_id: Optional[int] = None
    ) -> Optional[CorpTransactions]:
        """Get corporation wallet transactions."""
        token = self._get_token(character_id)
        if not token:
            return None

        corp_id = self.get_corporation_id(character_id)
        if not corp_id:
            return None

        result = self.esi.get_corporation_transactions(
            corp_id, division, token, from_id
        )

        type_ids = [t.get("type_id") for t in result]
        type_names = self.repo.resolve_type_names(type_ids)

        location_ids = [t.get("location_id") for t in result]
        location_names = self.repo.resolve_location_names(location_ids)

        transactions = []
        for txn in result:
            type_id = txn.get("type_id")
            location_id = txn.get("location_id")
            is_buy = txn.get("is_buy", False)
            quantity = txn.get("quantity", 0)

            transactions.append(CorpTransaction(
                transaction_id=txn.get("transaction_id"),
                date=txn.get("date"),
                type_id=type_id,
                type_name=type_names.get(type_id, "Unknown"),
                quantity=quantity if is_buy else -quantity,
                unit_price=txn.get("unit_price", 0),
                is_buy=is_buy,
                location_id=location_id,
                location_name=location_names.get(location_id, "Unknown"),
                client_id=txn.get("client_id", 0),
                wallet_division=division
            ))

        return CorpTransactions(corporation_id=corp_id, transactions=transactions)

    # SCD Type 2 - Corporation History

    def _update_corporation_history(self, character_id: int) -> bool:
        """Update SCD2 corporation history based on current ESI data.

        Compares current corp/alliance from ESI with the is_current record
        in character_corporation_history. If changed, closes old record
        and opens a new one.

        Uses corp history endpoint as authoritative source for corporation_id
        since the character info endpoint can return stale data.
        """
        try:
            info = self.esi.get_character_info(character_id)
            if not info:
                return False

            esi_corp_id = info.get("corporation_id")
            if not esi_corp_id:
                return False

            corp_id, hist_alliance_id = self._get_authoritative_corp(
                character_id, esi_corp_id
            )
            alliance_id = hist_alliance_id if corp_id != esi_corp_id else info.get("alliance_id")
            if not corp_id:
                return False

            with self.db.cursor() as cur:
                # Get current record
                cur.execute(
                    """
                    SELECT id, corporation_id, alliance_id
                    FROM character_corporation_history
                    WHERE character_id = %s AND is_current = TRUE
                    """,
                    (character_id,),
                )
                current = cur.fetchone()

                if current:
                    # Check if corp or alliance changed
                    if current["corporation_id"] == corp_id and current.get("alliance_id") == alliance_id:
                        return True  # No change

                    # Close old record
                    cur.execute(
                        """
                        UPDATE character_corporation_history
                        SET valid_to = NOW(), is_current = FALSE
                        WHERE id = %s
                        """,
                        (current["id"],),
                    )
                    logger.info(
                        f"Character {character_id} corp change: "
                        f"{current['corporation_id']} -> {corp_id}"
                    )

                # Insert new current record
                cur.execute(
                    """
                    INSERT INTO character_corporation_history
                        (character_id, corporation_id, alliance_id, valid_from, is_current)
                    VALUES (%s, %s, %s, NOW(), TRUE)
                    """,
                    (character_id, corp_id, alliance_id),
                )

            return True
        except Exception as e:
            logger.error(f"Corporation history update failed for {character_id}: {e}")
            return False

    # Sync methods

    def sync_character(self, character_id: int) -> dict:
        """Sync all character data."""
        results = {
            "wallet": False,
            "skills": False,
            "assets": False,
            "orders": False,
            "jobs": False,
            "blueprints": False,
            "corp_history": False,
            "implants": False,
        }

        # Invalidate cache
        self.repo.invalidate_cache(character_id)

        # SCD2: Track corporation changes (public endpoint, no token needed)
        try:
            if self._update_corporation_history(character_id):
                results["corp_history"] = True
        except Exception as e:
            logger.error(f"Corp history sync failed: {e}")

        try:
            wallet = self.get_wallet(character_id)
            if wallet:
                results["wallet"] = True
                self.repo.persist_wallet(character_id, wallet.balance)
        except Exception as e:
            logger.error(f"Wallet sync failed: {e}")

        try:
            skills = self.get_skills(character_id)
            if skills:
                results["skills"] = True
                skill_dicts = [
                    {
                        "skill_id": s.skill_id,
                        "active_skill_level": s.level,
                        "trained_skill_level": s.trained_level,
                        "skillpoints_in_skill": s.skillpoints,
                    }
                    for s in skills.skills
                ]
                self.repo.persist_skills(character_id, skill_dicts)
        except Exception as e:
            logger.error(f"Skills sync failed: {e}")

        try:
            queue = self.get_skillqueue(character_id)
            if queue:
                results["skillqueue"] = True
                queue_dicts = [
                    {
                        "queue_position": q.queue_position,
                        "skill_id": q.skill_id,
                        "finished_level": q.finished_level,
                        "start_date": q.start_date,
                        "finish_date": q.finish_date,
                        "training_start_sp": q.training_start_sp,
                        "level_start_sp": q.level_start_sp,
                        "level_end_sp": q.level_end_sp,
                    }
                    for q in queue.queue
                ]
                self.repo.persist_skillqueue(character_id, queue_dicts)
        except Exception as e:
            logger.error(f"Skillqueue sync failed: {e}")

        try:
            assets = self.get_assets(character_id)
            if assets:
                results["assets"] = True
                # Cache assets
                self.repo.save_assets(character_id, [
                    {
                        "type_id": a.type_id,
                        "type_name": a.type_name,
                        "quantity": a.quantity,
                        "location_id": a.location_id,
                        "location_name": a.location_name,
                        "location_type": a.location_type
                    }
                    for a in assets.assets
                ])
        except Exception as e:
            logger.error(f"Assets sync failed: {e}")

        try:
            orders = self.get_orders(character_id)
            if orders and orders.orders:
                results["orders"] = True
                self.repo.persist_orders(
                    character_id,
                    [o.model_dump(by_alias=True) for o in orders.orders],
                )
        except Exception as e:
            logger.error(f"Orders sync failed: {e}")

        try:
            jobs = self.get_industry_jobs(character_id)
            if jobs and jobs.jobs:
                results["jobs"] = True
                self.repo.persist_industry_jobs(
                    character_id,
                    [j.model_dump() for j in jobs.jobs],
                )
        except Exception as e:
            logger.error(f"Jobs sync failed: {e}")

        try:
            if self.get_blueprints(character_id):
                results["blueprints"] = True
        except Exception as e:
            logger.error(f"Blueprints sync failed: {e}")

        try:
            location = self.get_location(character_id)
            if location:
                results["location"] = True
                self.repo.persist_location(character_id, {
                    "solar_system_id": location.solar_system_id,
                    "station_id": location.station_id,
                    "structure_id": location.structure_id,
                })
        except Exception as e:
            logger.error(f"Location sync failed: {e}")

        try:
            ship = self.get_ship(character_id)
            if ship:
                results["ship"] = True
                self.repo.persist_ship(character_id, {
                    "ship_item_id": ship.ship_item_id,
                    "ship_type_id": ship.ship_type_id,
                    "ship_name": ship.ship_name,
                    "ship_type_name": ship.ship_type_name,
                })
        except Exception as e:
            logger.error(f"Ship sync failed: {e}")

        try:
            implant_ids = self.esi.get_implants(character_id, self._get_token(character_id))
            if implant_ids is not None:
                self.repo.persist_implants(character_id, implant_ids)
                results["implants"] = True
        except Exception as e:
            logger.error(f"Implants sync failed: {e}")

        # Update sync status timestamps
        try:
            self.repo.update_sync_status(character_id, results)
        except Exception as e:
            logger.error(f"Failed to update sync status: {e}")

        return results

    def get_all_characters(self) -> List[dict]:
        """Get all authenticated characters."""
        return self.repo.get_all_characters()
