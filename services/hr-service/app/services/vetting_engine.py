"""Automated Vetting Engine - Applicant screening pipeline.

Pipeline stages:
1. Red List intersection (contacts, wallet partners, corp history)
2. Wallet heuristics (suspicious transaction patterns)
3. Skill injection detection (SP delta analysis)
4. Risk score calculation (weighted formula)
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

import httpx

from eve_shared import get_db

from app.config import settings
from app.services.red_list_checker import RedListChecker

logger = logging.getLogger(__name__)

# Risk score weights
WEIGHT_RED_LIST = 30
WEIGHT_WALLET = 25
WEIGHT_SKILL_INJECTION = 20
WEIGHT_CHAR_AGE = 10
WEIGHT_CORP_HISTORY = 15

# Suspicious transaction ref_types from spec (Section 2.2.1)
SUSPICIOUS_REF_TYPES = {
    "player_trading": 10,     # Direct trade - high risk
    "player_donation": 8,     # Direct ISK transfer
    "corporation_account_withdrawal": 5,  # Corp wallet access
}


class VettingEngine:
    """Automated character vetting pipeline."""

    def __init__(self):
        self.db = get_db()
        self.red_list = RedListChecker()

    async def check_applicant(
        self,
        character_id: int,
        check_contacts: bool = True,
        check_wallet: bool = True,
        check_skills: bool = True,
    ) -> Dict[str, Any]:
        """Run full vetting pipeline for a character."""
        flags: Dict[str, Any] = {}
        red_list_hits: List[Dict[str, Any]] = []
        wallet_flags: List[Dict[str, Any]] = []
        skill_flags: List[Dict[str, Any]] = []
        risk_score = 0

        # Fetch character info from character-service
        char_info = await self._fetch_character_info(character_id)
        character_name = char_info.get("name", "Unknown") if char_info else "Unknown"

        # Stage 1: Red List intersection
        if check_contacts:
            contacts = await self._fetch_contacts(character_id)
            if contacts:
                contact_ids = [c.get("contact_id") for c in contacts if c.get("contact_id")]
                hits = self.red_list.intersect_contacts(contact_ids)
                if hits:
                    red_list_hits = hits
                    max_severity = max(h.get("severity", 1) for h in hits)
                    risk_score += min(WEIGHT_RED_LIST, WEIGHT_RED_LIST * max_severity // 5)
                    flags["red_list_contacts"] = len(hits)

        # Stage 2: Wallet heuristics
        if check_wallet:
            wallet_result = await self._analyze_wallet(character_id)
            if wallet_result.get("flags"):
                wallet_flags = wallet_result["flags"]
                risk_score += min(WEIGHT_WALLET, wallet_result.get("risk_add", 0))
                flags["suspicious_transactions"] = len(wallet_flags)

        # Stage 3: Skill injection detection
        if check_skills:
            skill_result = await self._detect_skill_injection(character_id)
            if skill_result.get("injected"):
                skill_flags = skill_result["flags"]
                risk_score += WEIGHT_SKILL_INJECTION
                flags["sp_injection"] = True
                flags["estimated_injectors"] = skill_result.get("estimated_injectors", 0)

        # Stage 4: Character age check
        if char_info:
            age_days = self._calculate_char_age(char_info)
            if age_days is not None and age_days < 90:
                risk_score += WEIGHT_CHAR_AGE
                flags["young_character"] = True
                flags["age_days"] = age_days

        # Stage 5: Corporation history scoring
        corp_result = await self._score_corp_history(character_id)
        if corp_result["score"] > 0:
            risk_score += corp_result["score"]
            if corp_result["flags"]:
                flags["corp_history"] = corp_result["flags"]

        risk_score = min(100, risk_score)

        # Store report
        report = self._store_report(
            character_id=character_id,
            character_name=character_name,
            risk_score=risk_score,
            flags=flags,
            red_list_hits=red_list_hits,
            wallet_flags=wallet_flags,
            skill_flags=skill_flags,
        )

        return report

    def get_report(self, character_id: int) -> Optional[Dict[str, Any]]:
        """Get latest vetting report for a character."""
        with self.db.cursor() as cur:
            cur.execute(
                """
                SELECT id, character_id, character_name, risk_score, flags,
                       red_list_hits, wallet_flags, skill_flags, checked_at
                FROM vetting_reports
                WHERE character_id = %(character_id)s
                ORDER BY checked_at DESC
                LIMIT 1
                """,
                {"character_id": character_id},
            )
            row = cur.fetchone()

        return dict(row) if row else None

    def get_history(self, character_id: int) -> List[Dict[str, Any]]:
        """Get all vetting reports for a character."""
        with self.db.cursor() as cur:
            cur.execute(
                """
                SELECT id, character_id, character_name, risk_score, flags,
                       red_list_hits, wallet_flags, skill_flags, checked_at
                FROM vetting_reports
                WHERE character_id = %(character_id)s
                ORDER BY checked_at DESC
                """,
                {"character_id": character_id},
            )
            rows = cur.fetchall()

        return [dict(r) for r in rows]

    # --- Internal Pipeline Stages ---

    async def _fetch_character_info(self, character_id: int) -> Optional[Dict]:
        """Fetch character info from character-service."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{settings.character_service_url}/api/character/{character_id}/info"
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            logger.warning(f"Failed to fetch character info for {character_id}")
        return None

    async def _fetch_contacts(self, character_id: int) -> List[Dict]:
        """Fetch character contacts from character-service (ESI proxy)."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{settings.character_service_url}/api/character/{character_id}/contacts"
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            logger.warning(f"Failed to fetch contacts for {character_id}")
        return []

    async def _analyze_wallet(self, character_id: int) -> Dict[str, Any]:
        """Analyze wallet journal for suspicious patterns."""
        result: Dict[str, Any] = {"flags": [], "risk_add": 0}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{settings.character_service_url}/api/character/{character_id}/wallet/journal"
                )
                if resp.status_code != 200:
                    return result
                journal = resp.json()
        except Exception:
            return result

        if not isinstance(journal, list):
            return result

        # Check for suspicious transaction patterns
        risk_add = 0
        for entry in journal:
            ref_type = entry.get("ref_type", "")
            if ref_type in SUSPICIOUS_REF_TYPES:
                amount = abs(entry.get("amount", 0))
                weight = SUSPICIOUS_REF_TYPES[ref_type]

                # Large donations/trades are more suspicious
                if amount > 100_000_000:  # >100M ISK
                    weight *= 2
                elif amount > 1_000_000_000:  # >1B ISK
                    weight *= 3

                result["flags"].append({
                    "ref_type": ref_type,
                    "amount": entry.get("amount"),
                    "date": entry.get("date"),
                    "first_party_id": entry.get("first_party_id"),
                    "second_party_id": entry.get("second_party_id"),
                    "risk_weight": weight,
                })
                risk_add += weight

        result["risk_add"] = min(WEIGHT_WALLET, risk_add)
        return result

    async def _detect_skill_injection(self, character_id: int) -> Dict[str, Any]:
        """Detect skill injection via SP delta analysis (Spec Section 2.3)."""
        result: Dict[str, Any] = {"injected": False, "flags": [], "estimated_injectors": 0}

        # Get current SP from character-service
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{settings.character_service_url}/api/character/{character_id}/skills"
                )
                if resp.status_code != 200:
                    return result
                skills_data = resp.json()
        except Exception:
            return result

        current_sp = skills_data.get("total_sp", 0)
        unallocated_sp = skills_data.get("unallocated_sp", 0)

        if not current_sp:
            return result

        # Get last snapshot
        with self.db.cursor() as cur:
            cur.execute(
                """
                SELECT total_sp, unallocated_sp, snapshot_at
                FROM skill_history_snapshots
                WHERE character_id = %(character_id)s
                ORDER BY snapshot_at DESC
                LIMIT 1
                """,
                {"character_id": character_id},
            )
            last_snapshot = cur.fetchone()

        # Store current snapshot
        with self.db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO skill_history_snapshots (character_id, total_sp, unallocated_sp)
                VALUES (%(character_id)s, %(total_sp)s, %(unallocated_sp)s)
                ON CONFLICT (character_id, snapshot_at) DO NOTHING
                """,
                {
                    "character_id": character_id,
                    "total_sp": current_sp,
                    "unallocated_sp": unallocated_sp,
                },
            )
            
        if not last_snapshot:
            return result

        # Delta analysis (Spec Section 2.3.2)
        last_sp = last_snapshot["total_sp"]
        last_time = last_snapshot["snapshot_at"]
        hours_elapsed = (datetime.utcnow() - last_time.replace(tzinfo=None)).total_seconds() / 3600

        if hours_elapsed < 0.5:
            return result

        sp_delta = current_sp - last_sp
        max_natural_sp = (settings.sp_rate_threshold + settings.sp_rate_buffer) * hours_elapsed

        if sp_delta > max_natural_sp:
            injected_sp = sp_delta - (settings.sp_rate_threshold * hours_elapsed)
            # Estimate injectors based on SP brackets
            estimated = 0
            if current_sp < 5_000_000:
                estimated = int(injected_sp / 500_000)
            elif current_sp < 50_000_000:
                estimated = int(injected_sp / 400_000)
            elif current_sp < 80_000_000:
                estimated = int(injected_sp / 300_000)
            else:
                estimated = int(injected_sp / 150_000)

            result["injected"] = True
            result["estimated_injectors"] = max(1, estimated)
            result["flags"].append({
                "type": "sp_injection_detected",
                "sp_delta": sp_delta,
                "max_natural": int(max_natural_sp),
                "hours_elapsed": round(hours_elapsed, 1),
                "estimated_injectors": result["estimated_injectors"],
            })

        return result

    async def _score_corp_history(self, character_id: int) -> Dict[str, Any]:
        """Score corporation history for suspicious patterns.

        Flags:
        - Frequent corp hopping (>5 corps in 6 months)
        - Very short tenure in recent corps (<7 days)
        - NPC corp cycling pattern (cyno alt indicator)
        """
        flags: List[str] = []
        score = 0

        with self.db.cursor() as cur:
            cur.execute("""
                SELECT corporation_id, start_date
                FROM character_corporation_history
                WHERE character_id = %(cid)s
                ORDER BY start_date DESC
            """, {"cid": character_id})
            history = cur.fetchall()

        if not history:
            return {"score": 0, "flags": ["no_corp_history"]}

        from datetime import timezone, timedelta

        # 1. Frequent hopping: >5 corps in last 6 months
        six_months_ago = datetime.now(timezone.utc) - timedelta(days=180)
        recent_corps = [
            h for h in history
            if h["start_date"] and h["start_date"].replace(tzinfo=timezone.utc) > six_months_ago
        ]
        if len(recent_corps) > 5:
            score += 8
            flags.append(f"corp_hopping:{len(recent_corps)}_in_6mo")

        # 2. Short tenure in recent corps (<7 days)
        for i in range(min(3, len(history) - 1)):
            current = history[i]
            previous = history[i + 1]
            if current["start_date"] and previous["start_date"]:
                tenure_days = (current["start_date"] - previous["start_date"]).days
                if 0 < tenure_days < 7:
                    score += 3
                    flags.append(f"short_tenure:{tenure_days}d")

        # 3. NPC corp cycling pattern (cyno alt indicator)
        NPC_CORPS = {
            1000001, 1000002, 1000003, 1000004, 1000005, 1000006,
            1000007, 1000008, 1000009, 1000010, 1000011, 1000012,
            1000125, 1000127, 1000128, 1000130,
            1000166, 1000167, 1000168, 1000169,
        }
        npc_switches = 0
        for i in range(len(history) - 1):
            is_npc = history[i]["corporation_id"] in NPC_CORPS
            was_npc = history[i + 1]["corporation_id"] in NPC_CORPS
            if is_npc != was_npc:
                npc_switches += 1
        if npc_switches >= 4:
            score += 5
            flags.append(f"npc_cycling:{npc_switches}_switches")

        # Cap at WEIGHT_CORP_HISTORY
        score = min(score, WEIGHT_CORP_HISTORY)

        return {"score": score, "flags": flags}

    def _calculate_char_age(self, char_info: Dict) -> Optional[int]:
        """Calculate character age in days."""
        birthday = char_info.get("birthday")
        if not birthday:
            return None
        try:
            if isinstance(birthday, str):
                bd = datetime.fromisoformat(birthday.replace("Z", "+00:00"))
            else:
                bd = birthday
            return (datetime.utcnow() - bd.replace(tzinfo=None)).days
        except Exception:
            return None

    def _store_report(self, **kwargs) -> Dict[str, Any]:
        """Store vetting report in database."""
        import json

        with self.db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO vetting_reports
                    (character_id, character_name, risk_score, flags,
                     red_list_hits, wallet_flags, skill_flags)
                VALUES
                    (%(character_id)s, %(character_name)s, %(risk_score)s,
                     %(flags)s::jsonb, %(red_list_hits)s::jsonb,
                     %(wallet_flags)s::jsonb, %(skill_flags)s::jsonb)
                RETURNING id, character_id, character_name, risk_score,
                          flags, red_list_hits, wallet_flags, skill_flags, checked_at
                """,
                {
                    "character_id": kwargs["character_id"],
                    "character_name": kwargs["character_name"],
                    "risk_score": kwargs["risk_score"],
                    "flags": json.dumps(kwargs["flags"]),
                    "red_list_hits": json.dumps(kwargs["red_list_hits"]),
                    "wallet_flags": json.dumps(kwargs["wallet_flags"]),
                    "skill_flags": json.dumps(kwargs["skill_flags"]),
                },
            )
            row = cur.fetchone()
            
        return dict(row)
