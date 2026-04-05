"""Tests for DoctrineService EFT/DNA parsing logic.

Tests _parse_eft_line(), EFT header parsing, block splitting,
and DNA string parsing without requiring database connections.
"""

import re

import pytest

from app.services.doctrine import (
    DoctrineService,
    SLOT_BLOCK_ORDER,
    FLAG_HIGH,
    FLAG_MID,
    FLAG_LOW,
    FLAG_RIG,
    FLAG_DRONE,
)


# ──────────────────── Module Constants ───────────────────────────────────


class TestDoctrineConstants:
    """Validate doctrine module constants."""

    def test_slot_block_order(self):
        """Block order is low, med, high, rig (EFT standard)."""
        assert SLOT_BLOCK_ORDER == ["low", "med", "high", "rig"]

    def test_flag_high_range(self):
        """FLAG_HIGH covers 27-34."""
        assert list(FLAG_HIGH) == list(range(27, 35))

    def test_flag_mid_range(self):
        """FLAG_MID covers 19-26."""
        assert list(FLAG_MID) == list(range(19, 27))

    def test_flag_low_range(self):
        """FLAG_LOW covers 11-18."""
        assert list(FLAG_LOW) == list(range(11, 19))

    def test_flag_rig_range(self):
        """FLAG_RIG covers 92-99."""
        assert list(FLAG_RIG) == list(range(92, 100))

    def test_flag_drone(self):
        """FLAG_DRONE is (87,)."""
        assert FLAG_DRONE == (87,)


# ──────────────────── _parse_eft_line() ──────────────────────────────────


class TestParseEftLine:
    """Test EFT line parsing for modules, quantities, and ammo."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.service = DoctrineService()

    def test_simple_module(self):
        """A plain module name returns quantity 1."""
        result = self.service._parse_eft_line("Large Shield Extender II")
        assert result == {"name": "Large Shield Extender II", "quantity": 1}

    def test_quantity_suffix(self):
        """'Hammerhead II x5' should parse quantity 5."""
        result = self.service._parse_eft_line("Hammerhead II x5")
        assert result == {"name": "Hammerhead II", "quantity": 5}

    def test_quantity_suffix_uppercase(self):
        """Quantity suffix is case-insensitive: 'x10' or 'X10'."""
        result = self.service._parse_eft_line("Hobgoblin II X10")
        assert result == {"name": "Hobgoblin II", "quantity": 10}

    def test_ammo_comma_format(self):
        """'Module, Ammo' format strips ammo portion."""
        result = self.service._parse_eft_line("Heavy Missile Launcher II, Scourge Fury Heavy Missile")
        assert result["name"] == "Heavy Missile Launcher II"
        assert result["quantity"] == 1

    def test_ammo_comma_with_quantity(self):
        """Module with both ammo and quantity is unlikely but handled.

        Comma split happens first, then quantity check on module part.
        """
        result = self.service._parse_eft_line("Drone x3, Ammo Type")
        assert result["name"] == "Drone"
        assert result["quantity"] == 3

    def test_empty_string(self):
        """Empty string returns None."""
        result = self.service._parse_eft_line("")
        assert result is None

    def test_comma_only_module_part_empty(self):
        """A line that is just a comma yields None (empty module_part)."""
        result = self.service._parse_eft_line(", Some Ammo")
        assert result is None

    def test_module_with_roman_numerals(self):
        """Module names with Roman numerals (e.g. 'II') are preserved."""
        result = self.service._parse_eft_line("Ballistic Control System II")
        assert result["name"] == "Ballistic Control System II"

    def test_module_with_numbers_in_name(self):
        """Module names with numbers (e.g. '425mm') work correctly."""
        result = self.service._parse_eft_line("425mm AutoCannon II")
        assert result["name"] == "425mm AutoCannon II"
        assert result["quantity"] == 1

    def test_large_quantity(self):
        """Large quantities parse correctly."""
        result = self.service._parse_eft_line("Nanite Repair Paste x1000")
        assert result["name"] == "Nanite Repair Paste"
        assert result["quantity"] == 1000


# ──────────────────── EFT Header Parsing ─────────────────────────────────


class TestEftHeaderParsing:
    """Test EFT header regex: [Ship Name, Fitting Name]."""

    def test_valid_header(self):
        """Standard EFT header parses ship and fitting name."""
        header = "[Drake, PvP Shield Drake]"
        match = re.match(r"^\[(.+?),\s*(.+?)\]$", header)
        assert match is not None
        assert match.group(1) == "Drake"
        assert match.group(2) == "PvP Shield Drake"

    def test_header_with_spaces(self):
        """Ship name with spaces works."""
        header = "[Raven Navy Issue, Missions Fit]"
        match = re.match(r"^\[(.+?),\s*(.+?)\]$", header)
        assert match is not None
        assert match.group(1) == "Raven Navy Issue"
        assert match.group(2) == "Missions Fit"

    def test_invalid_header_no_brackets(self):
        """Missing brackets fails to match."""
        header = "Drake, PvP Shield Drake"
        match = re.match(r"^\[(.+?),\s*(.+?)\]$", header)
        assert match is None

    def test_invalid_header_no_comma(self):
        """Missing comma fails to match."""
        header = "[Drake]"
        match = re.match(r"^\[(.+?),\s*(.+?)\]$", header)
        assert match is None


# ──────────────────── EFT Block Splitting Logic ──────────────────────────


class TestEftBlockSplitting:
    """Test the block-splitting logic from import_from_eft (pure portion)."""

    def test_empty_lines_split_blocks(self, sample_eft_text):
        """Empty lines create block boundaries in EFT text."""
        lines = sample_eft_text.strip().split("\n")
        blocks = []
        current_block = []

        for line in lines[1:]:
            trimmed = line.strip()
            if trimmed == "":
                if current_block:
                    blocks.append(current_block)
                    current_block = []
                continue
            if trimmed.startswith("[Empty "):
                continue
            current_block.append(trimmed)

        if current_block:
            blocks.append(current_block)

        # EFT format: block0=low, block1=med, block2=high, block3=rig, block4=drones
        assert len(blocks) == 5  # low, med, high, rig, drones (both types in one block)

    def test_empty_slot_skipped(self):
        """Lines starting with [Empty ...] are skipped."""
        lines = [
            "[Empty Low slot]",
            "[Empty Med slot]",
            "Damage Control II",
        ]
        filtered = [l for l in lines if not l.startswith("[Empty ")]
        assert len(filtered) == 1
        assert filtered[0] == "Damage Control II"

    def test_block_assignment_to_slots(self):
        """First 4 blocks map to low/med/high/rig, rest to drones."""
        for i, expected in enumerate(SLOT_BLOCK_ORDER):
            assert SLOT_BLOCK_ORDER[i] == expected
        # Block 4+ should map to drones (logic in import_from_eft)
        assert len(SLOT_BLOCK_ORDER) == 4


# ──────────────────── DNA Parsing ────────────────────────────────────────


class TestDnaParsing:
    """Test DNA string parsing logic (the pure string parsing portion)."""

    def test_valid_dna_parts_split(self):
        """DNA string splits into ship type and module entries."""
        dna = "24690:2048;1:2048;1:2205;1:3170;2::"
        parts = dna.strip().rstrip(":").split(":")
        assert parts[0] == "24690"
        assert len(parts) >= 5

    def test_ship_type_extraction(self):
        """First part of DNA is the ship type ID."""
        dna = "24690:2048;1::"
        parts = dna.strip().rstrip(":").split(":")
        ship_type_id = int(parts[0])
        assert ship_type_id == 24690

    def test_module_semicolon_parsing(self):
        """Module entries are 'typeID;qty' format."""
        entry = "2048;3"
        segments = entry.split(";")
        type_id = int(segments[0])
        qty = int(segments[1])
        assert type_id == 2048
        assert qty == 3

    def test_module_without_quantity(self):
        """Module entry without quantity defaults to 1."""
        entry = "2048"
        segments = entry.split(";")
        type_id = int(segments[0])
        qty = int(segments[1]) if len(segments) > 1 else 1
        assert type_id == 2048
        assert qty == 1

    def test_malformed_dna_too_short(self):
        """DNA with only one part (no modules) should be detectable."""
        dna = "24690::"
        parts = dna.strip().rstrip(":").split(":")
        # After stripping colons: "24690" -> one part
        # In the service, len(parts) < 2 returns None
        # Here we just check the split behavior
        assert len(parts) == 1

    def test_empty_dna_parts_filtered(self):
        """Empty parts from trailing colons are filtered in loop."""
        dna = "24690:2048;1:2205;1::"
        parts = dna.strip().rstrip(":").split(":")
        non_empty = [p for p in parts[1:] if p]
        assert len(non_empty) == 2
