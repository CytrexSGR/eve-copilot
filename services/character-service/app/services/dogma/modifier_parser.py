"""Parse modifierInfo YAML from dgmEffects into structured modifier objects."""

import functools
import logging
from dataclasses import dataclass
from typing import List, Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DogmaModifier:
    domain: str                    # shipID, itemID, charID, etc.
    func: str                      # ItemModifier, LocationGroupModifier, etc.
    modified_attr_id: int          # target attribute to change
    modifying_attr_id: int         # source attribute providing the value
    operation: int                 # 0,2,3,4,5,6,7,9
    group_id: Optional[int] = None           # for LocationGroupModifier
    skill_type_id: Optional[int] = None      # for LocationRequiredSkillModifier
    is_drawback: bool = False                # rig drawback effects (not stacking penalized)
    is_rig: bool = False                     # rig bonus effects (not stacking penalized in EVE)
    is_role_bonus: bool = False              # ship role bonus (flat, not per-level)
    is_skill: bool = False                   # skill-origin modifier (NOT stacking penalized in EVE)
    scaling_skill_id: Optional[int] = None   # skill ID for per-level scaling (T2 ships: skill1 vs skill2)
    effect_category: Optional[int] = None    # effectCategory from dgmEffects (0=passive,1=active,4=online,5=overload)


@functools.lru_cache(maxsize=2048)
def _parse_modifier_info_cached(yaml_text: str) -> tuple:
    """Parse and cache modifierInfo YAML. Returns immutable tuple for safe caching."""
    try:
        data = yaml.safe_load(yaml_text)
    except yaml.YAMLError:
        logger.debug("Failed to parse modifierInfo YAML")
        return ()
    if not isinstance(data, list):
        return ()
    modifiers = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        try:
            modifiers.append(DogmaModifier(
                domain=entry.get("domain", ""),
                func=entry.get("func", ""),
                modified_attr_id=int(entry["modifiedAttributeID"]),
                modifying_attr_id=int(entry["modifyingAttributeID"]),
                operation=int(entry.get("operation", 0)),
                group_id=int(entry["groupID"]) if "groupID" in entry else None,
                skill_type_id=int(entry["skillTypeID"]) if "skillTypeID" in entry else None,
            ))
        except (KeyError, ValueError, TypeError):
            continue
    return tuple(modifiers)


def parse_modifier_info(yaml_text: Optional[str]) -> List[DogmaModifier]:
    """Parse modifierInfo YAML string into list of DogmaModifier objects.

    Results are cached internally — repeated calls with the same YAML text
    skip re-parsing (~200-400 calls per fitting request).
    """
    if not yaml_text:
        return []
    return list(_parse_modifier_info_cached(yaml_text))
