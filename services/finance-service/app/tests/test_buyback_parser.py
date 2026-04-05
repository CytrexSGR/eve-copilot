"""Tests for BuybackService parsing logic.

Tests parse_eve_text(), _parse_quantity(), and _is_ore_or_mineral()
without requiring database connections.
"""

import pytest

from app.services.buyback import BuybackService


# ──────────────────── parse_eve_text() ───────────────────────────────────


class TestParseEveText:
    """Test EVE client text parsing into item lists."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.service = BuybackService(db=None)

    def test_tsv_format(self):
        """Tab-separated values: 'Item\\tQuantity'."""
        text = "Tritanium\t10000"
        result = self.service.parse_eve_text(text)
        assert len(result) == 1
        assert result[0]["name"] == "Tritanium"
        assert result[0]["quantity"] == 10000

    def test_tsv_multiple_columns(self):
        """TSV with extra columns (EVE inventory has type, quantity, group, etc.)."""
        text = "Tritanium\t10000\tMineral\t1.0 m3"
        result = self.service.parse_eve_text(text)
        assert result[0]["name"] == "Tritanium"
        assert result[0]["quantity"] == 10000

    def test_x_format_with_space(self):
        """'Item x Quantity' format."""
        text = "Pyerite x 5000"
        result = self.service.parse_eve_text(text)
        assert result[0]["name"] == "Pyerite"
        assert result[0]["quantity"] == 5000

    def test_x_format_no_space(self):
        """'Item x5000' format (no space after x)."""
        text = "Pyerite x5000"
        result = self.service.parse_eve_text(text)
        assert result[0]["name"] == "Pyerite"
        assert result[0]["quantity"] == 5000

    def test_number_at_end_format(self):
        """'Item Quantity' format (number at end)."""
        text = "Mexallon 2000"
        result = self.service.parse_eve_text(text)
        assert result[0]["name"] == "Mexallon"
        assert result[0]["quantity"] == 2000

    def test_single_item_no_quantity(self):
        """Single item name without quantity defaults to 1."""
        text = "Tritanium"
        result = self.service.parse_eve_text(text)
        assert result[0]["name"] == "Tritanium"
        assert result[0]["quantity"] == 1

    def test_empty_input(self):
        """Empty input returns empty list."""
        result = self.service.parse_eve_text("")
        assert result == []

    def test_whitespace_only_input(self):
        """Whitespace-only input returns empty list."""
        result = self.service.parse_eve_text("   \n  \n  ")
        assert result == []

    def test_multiple_lines_mixed_formats(self):
        """Multiple lines with different formats."""
        text = "Tritanium\t10000\nPyerite x 5000\nMexallon 2000\nIsogen"
        result = self.service.parse_eve_text(text)
        assert len(result) == 4
        assert result[0] == {"name": "Tritanium", "quantity": 10000}
        assert result[1] == {"name": "Pyerite", "quantity": 5000}
        assert result[2] == {"name": "Mexallon", "quantity": 2000}
        assert result[3] == {"name": "Isogen", "quantity": 1}

    def test_european_number_format(self):
        """Dots as thousands separators are stripped: '10.000' -> 10000."""
        text = "Tritanium\t10.000"
        result = self.service.parse_eve_text(text)
        assert result[0]["quantity"] == 10000

    def test_comma_thousands_separator(self):
        """Commas as thousands separators are stripped: '10,000' -> 10000."""
        text = "Tritanium\t10,000"
        result = self.service.parse_eve_text(text)
        assert result[0]["quantity"] == 10000

    def test_quantity_zero_becomes_one(self):
        """Quantity of 0 is clamped to 1 (min quantity)."""
        text = "Tritanium\t0"
        result = self.service.parse_eve_text(text)
        assert result[0]["quantity"] == 1

    def test_empty_lines_between_items(self):
        """Empty lines between items are skipped."""
        text = "Tritanium\t100\n\n\nPyerite\t200"
        result = self.service.parse_eve_text(text)
        assert len(result) == 2


# ──────────────────── _parse_quantity() ──────────────────────────────────


class TestParseQuantity:
    """Test quantity string parsing."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.service = BuybackService(db=None)

    def test_simple_integer(self):
        """Plain integer string."""
        assert self.service._parse_quantity("100") == 100

    def test_commas_stripped(self):
        """Comma-separated thousands."""
        assert self.service._parse_quantity("1,000,000") == 1000000

    def test_dots_stripped(self):
        """Dot-separated thousands (European format)."""
        assert self.service._parse_quantity("1.000.000") == 1000000

    def test_invalid_returns_one(self):
        """Non-numeric strings return 1."""
        assert self.service._parse_quantity("abc") == 1

    def test_whitespace_stripped(self):
        """Leading/trailing whitespace is stripped."""
        assert self.service._parse_quantity("  500  ") == 500


# ──────────────────── _is_ore_or_mineral() ───────────────────────────────


class TestIsOreOrMineral:
    """Test ore/mineral classification heuristic."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.service = BuybackService(db=None)

    # All 8 minerals
    @pytest.mark.parametrize("mineral", [
        "Tritanium", "Pyerite", "Mexallon", "Isogen",
        "Nocxium", "Zydrine", "Megacyte", "Morphite",
    ])
    def test_all_minerals(self, mineral):
        """All 8 base minerals should be classified as ore/mineral."""
        assert self.service._is_ore_or_mineral(mineral) is True

    # Ore keyword matches
    @pytest.mark.parametrize("ore_name", [
        "Veldspar", "Concentrated Veldspar", "Dense Veldspar",
        "Scordite", "Condensed Scordite",
        "Pyroxeres", "Plagioclase",
        "Omber", "Kernite", "Jaspet",
        "Hemorphite", "Hedbergite",
        "Gneiss", "Dark Ochre", "Spodumain",
        "Crokite", "Bistot", "Arkonor", "Mercoxit",
        "Compressed Veldspar", "Compressed Scordite",
    ])
    def test_ore_keyword_match(self, ore_name):
        """Ore names containing known keywords should match."""
        assert self.service._is_ore_or_mineral(ore_name) is True

    def test_ice_keyword(self):
        """'Ice' keyword should match."""
        assert self.service._is_ore_or_mineral("Blue Ice") is True
        assert self.service._is_ore_or_mineral("White Glaze Ice") is True

    def test_compressed_keyword(self):
        """'Compressed' keyword should match."""
        assert self.service._is_ore_or_mineral("Compressed Tritanium") is True

    # Non-ore items
    @pytest.mark.parametrize("non_ore", [
        "Raven Navy Issue",
        "Large Shield Extender II",
        "Hammerhead II",
        "Scourge Fury Heavy Missile",
        "Damage Control II",
        "Antimatter Charge L",
    ])
    def test_non_ore_items(self, non_ore):
        """Non-ore/mineral items should return False."""
        assert self.service._is_ore_or_mineral(non_ore) is False

    def test_case_insensitive(self):
        """Mineral/ore check is case-insensitive."""
        assert self.service._is_ore_or_mineral("TRITANIUM") is True
        assert self.service._is_ore_or_mineral("tritanium") is True

    # New ore types from Equinox
    @pytest.mark.parametrize("new_ore", [
        "Bezdnacine", "Rakovene", "Talassonite",
        "Kylixium", "Nocxite", "Ueganite",
        "Hezorime", "Griemeer", "Mordunium",
    ])
    def test_new_equinox_ores(self, new_ore):
        """New Equinox ore types should match."""
        assert self.service._is_ore_or_mineral(new_ore) is True
