"""
Org management repository — permissions, audit log, member queries.
Tables: org_permissions, org_audit_log, platform_accounts, platform_roles, account_characters
Pattern: db_cursor from app.database (RealDictCursor, auto-commit)
"""

import csv
import io
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from app.database import db_cursor

logger = logging.getLogger(__name__)

# Default permissions: permission -> list of roles that get it
DEFAULT_PERMISSIONS: Dict[str, List[str]] = {
    "members.view": ["admin", "officer"],
    "members.manage": ["admin"],
    "roles.manage": ["admin"],
    "finance.view": ["admin", "officer"],
    "hr.view": ["admin", "officer"],
    "hr.manage": ["admin"],
    "audit.view": ["admin", "officer"],
    "settings.manage": ["admin"],
    "fleet.create":    ["admin", "officer", "fleet_commander"],
    "fleet.manage":    ["admin", "officer", "fleet_commander"],
    "fleet.view":      ["admin", "officer", "fleet_commander", "member"],
    "ops.create":      ["admin", "officer", "fleet_commander"],
    "ops.manage":      ["admin", "officer", "fleet_commander"],
}

ALL_PERMISSIONS = list(DEFAULT_PERMISSIONS.keys())
VALID_ROLES = ["admin", "officer", "fleet_commander", "member"]


class OrgRepository:

    def init_default_permissions(self, corporation_id: int) -> int:
        """Insert default permissions for a corp. Returns count inserted."""
        count = 0
        with db_cursor() as cur:
            for permission, roles in DEFAULT_PERMISSIONS.items():
                for role in VALID_ROLES:
                    granted = role in roles
                    cur.execute(
                        """INSERT INTO org_permissions (corporation_id, role, permission, granted)
                           VALUES (%s, %s, %s, %s)
                           ON CONFLICT (corporation_id, role, permission) DO NOTHING""",
                        (corporation_id, role, permission, granted),
                    )
                    count += cur.rowcount
        return count

    def get_permissions(self, corporation_id: int) -> List[Dict[str, Any]]:
        with db_cursor() as cur:
            cur.execute(
                """SELECT role, permission, granted FROM org_permissions
                   WHERE corporation_id = %s ORDER BY permission, role""",
                (corporation_id,),
            )
            return [dict(r) for r in cur.fetchall()]

    def check_permission(self, corporation_id: int, role: str, permission: str) -> bool:
        with db_cursor() as cur:
            cur.execute(
                """SELECT granted FROM org_permissions
                   WHERE corporation_id = %s AND role = %s AND permission = %s""",
                (corporation_id, role, permission),
            )
            row = cur.fetchone()
            if not row:
                return role in DEFAULT_PERMISSIONS.get(permission, [])
            return row["granted"]

    def update_permissions(self, corporation_id: int, updates: List[Dict[str, Any]]) -> int:
        count = 0
        with db_cursor() as cur:
            for u in updates:
                cur.execute(
                    """INSERT INTO org_permissions (corporation_id, role, permission, granted)
                       VALUES (%s, %s, %s, %s)
                       ON CONFLICT (corporation_id, role, permission)
                       DO UPDATE SET granted = EXCLUDED.granted""",
                    (corporation_id, u["role"], u["permission"], u["granted"]),
                )
                count += cur.rowcount
        return count

    def get_members(self, corporation_id: int) -> List[Dict[str, Any]]:
        """Get all platform members for a corp with roles and token status."""
        with db_cursor() as cur:
            cur.execute(
                """SELECT
                       pa.id AS account_id,
                       pa.primary_character_id,
                       pa.primary_character_name,
                       pa.effective_tier,
                       pa.last_login,
                       pr.role,
                       ct.expires_at AS token_expires_at
                   FROM platform_accounts pa
                   LEFT JOIN platform_roles pr
                       ON pr.corporation_id = %s AND pr.character_id = pa.primary_character_id
                   LEFT JOIN character_tokens ct
                       ON ct.character_id = pa.primary_character_id
                   WHERE pa.corporation_id = %s
                   ORDER BY
                       CASE pr.role WHEN 'admin' THEN 0 WHEN 'officer' THEN 1 WHEN 'fleet_commander' THEN 2 ELSE 3 END,
                       pa.primary_character_name""",
                (corporation_id, corporation_id),
            )
            members = []
            now = datetime.now(timezone.utc)
            for row in cur.fetchall():
                r = dict(row)
                if not r.get("token_expires_at"):
                    r["token_status"] = "missing"
                elif r["token_expires_at"].replace(tzinfo=timezone.utc) < now:
                    r["token_status"] = "expired"
                else:
                    r["token_status"] = "valid"
                r.pop("token_expires_at", None)
                members.append(r)
            return members

    def get_overview(self, corporation_id: int) -> Dict[str, Any]:
        with db_cursor() as cur:
            cur.execute("SELECT COUNT(*) AS cnt FROM platform_accounts WHERE corporation_id = %s", (corporation_id,))
            member_count = cur.fetchone()["cnt"]

            cur.execute(
                """SELECT COUNT(*) AS total,
                       COUNT(*) FILTER (WHERE ct.expires_at > now()) AS valid_tokens
                   FROM platform_accounts pa
                   LEFT JOIN character_tokens ct ON ct.character_id = pa.primary_character_id
                   WHERE pa.corporation_id = %s""",
                (corporation_id,),
            )
            tokens = cur.fetchone()
            token_coverage = round(tokens["valid_tokens"] / tokens["total"] * 100, 1) if tokens["total"] > 0 else 0

            cur.execute(
                "SELECT COUNT(*) AS cnt FROM platform_accounts WHERE corporation_id = %s AND last_login > now() - interval '7 days'",
                (corporation_id,),
            )
            active_7d = cur.fetchone()["cnt"]

            cur.execute(
                """SELECT pr.role, COUNT(*) AS cnt
                   FROM platform_accounts pa
                   LEFT JOIN platform_roles pr ON pr.corporation_id = %s AND pr.character_id = pa.primary_character_id
                   WHERE pa.corporation_id = %s GROUP BY pr.role""",
                (corporation_id, corporation_id),
            )
            role_dist = {r["role"] or "unassigned": r["cnt"] for r in cur.fetchall()}

        return {
            "corporation_id": corporation_id,
            "member_count": member_count,
            "token_coverage_pct": token_coverage,
            "active_7d": active_7d,
            "role_distribution": role_dist,
        }

    def log_action(self, corporation_id, actor_character_id, actor_name, action, target_type=None, target_id=None, target_name=None, details=None):
        with db_cursor() as cur:
            cur.execute(
                """INSERT INTO org_audit_log (corporation_id, actor_character_id, actor_name, action, target_type, target_id, target_name, details)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                (corporation_id, actor_character_id, actor_name, action, target_type, target_id, target_name, json.dumps(details or {})),
            )
            return cur.fetchone()["id"]

    def get_audit_log(self, corporation_id, limit=50, offset=0, action_filter=None, actor_filter=None, date_from=None, date_to=None):
        conditions = ["corporation_id = %s"]
        params = [corporation_id]
        if action_filter:
            conditions.append("action = %s"); params.append(action_filter)
        if actor_filter:
            conditions.append("actor_character_id = %s"); params.append(actor_filter)
        if date_from:
            conditions.append("created_at >= %s"); params.append(date_from)
        if date_to:
            conditions.append("created_at <= %s"); params.append(date_to)
        where = " AND ".join(conditions)
        with db_cursor() as cur:
            cur.execute(f"SELECT COUNT(*) AS cnt FROM org_audit_log WHERE {where}", tuple(params))
            total = cur.fetchone()["cnt"]
            cur.execute(f"SELECT * FROM org_audit_log WHERE {where} ORDER BY created_at DESC LIMIT %s OFFSET %s", tuple(params) + (limit, offset))
            entries = [dict(r) for r in cur.fetchall()]
        return {"total": total, "entries": entries, "limit": limit, "offset": offset}

    def export_audit_csv(self, corporation_id):
        with db_cursor() as cur:
            cur.execute("SELECT created_at, actor_name, action, target_type, target_name, details FROM org_audit_log WHERE corporation_id = %s ORDER BY created_at DESC", (corporation_id,))
            rows = cur.fetchall()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Timestamp", "Actor", "Action", "Target Type", "Target", "Details"])
        for r in rows:
            writer.writerow([r["created_at"].isoformat(), r["actor_name"], r["action"], r["target_type"] or "", r["target_name"] or "", json.dumps(r["details"]) if r["details"] else ""])
        return output.getvalue()
