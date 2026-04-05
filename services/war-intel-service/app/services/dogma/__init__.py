# app/services/dogma/__init__.py
"""Dogma Engine - Killmail fitting analysis and tank/DPS calculations."""

from .models import (
    ResistProfile,
    ShipBaseStats,
    TankModuleEffect,
    FittedModule,
    TankResult,
    AttackerDPSResult,
    AttackerWeaponStats,
    KillmailAnalysis,
    FittingRequest,
    TankType,
    ModuleSlot,
)
from .repository import DogmaRepository
from .tank_calculator import TankCalculatorService, get_tank_calculator
from .fitting_analyzer import FittingAnalyzer, get_fitting_analyzer

__all__ = [
    # Models
    "ResistProfile",
    "ShipBaseStats",
    "TankModuleEffect",
    "FittedModule",
    "TankResult",
    "AttackerDPSResult",
    "AttackerWeaponStats",
    "KillmailAnalysis",
    "FittingRequest",
    "TankType",
    "ModuleSlot",
    # Services
    "DogmaRepository",
    "TankCalculatorService",
    "get_tank_calculator",
    "FittingAnalyzer",
    "get_fitting_analyzer",
]
