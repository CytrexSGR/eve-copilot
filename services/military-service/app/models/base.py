"""Base models with camelCase field aliases.

This module provides base Pydantic models that automatically convert
Python snake_case field names to JavaScript camelCase in API responses.

Backend code continues to use snake_case (Python convention), but
API consumers receive camelCase JSON (JavaScript convention).
"""

from pydantic import BaseModel, ConfigDict


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase.

    Args:
        string: Field name in snake_case (e.g., "total_kills")

    Returns:
        Field name in camelCase (e.g., "totalKills")

    Examples:
        >>> to_camel("total_kills")
        'totalKills'
        >>> to_camel("isk_destroyed")
        'iskDestroyed'
        >>> to_camel("alliance_id")
        'allianceId'
    """
    components = string.split('_')
    # First component stays lowercase, rest are title-cased
    return components[0] + "".join(x.title() for x in components[1:])


class CamelModel(BaseModel):
    """Base Pydantic model with automatic camelCase field aliasing.

    Use this as a base class for response models that need to convert
    Python snake_case field names to JavaScript camelCase.

    Backend continues using snake_case:
        class AllianceStats(CamelModel):
            total_kills: int
            isk_destroyed: float

    Frontend receives camelCase JSON:
        {"totalKills": 100, "iskDestroyed": 1234.56}

    The model also accepts both formats on input (populate_by_name=True),
    which is useful for testing and backwards compatibility.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Accept both snake_case and camelCase on input
    )
