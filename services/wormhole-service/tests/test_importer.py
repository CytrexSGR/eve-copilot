"""Tests for wormhole data importer."""
import pytest
from app.services.importer import WormholeImporter


class TestWormholeImporter:
    """Test data import functionality."""

    def test_parse_statics_csv(self):
        """Test parsing Pathfinder system_static.csv."""
        csv_content = """id,systemId,typeId
1,31000001,30583
2,31000001,30584
3,31000002,30642"""

        importer = WormholeImporter()
        result = importer.parse_statics_csv(csv_content)

        assert len(result) == 3
        assert result[0] == {'system_id': 31000001, 'type_id': 30583}

    def test_parse_wormhole_csv(self):
        """Test parsing Pathfinder wormhole.csv."""
        csv_content = """id,name,scanWormholeStrength
1,A009,10
2,B274,5
3,C125,"""

        importer = WormholeImporter()
        result = importer.parse_wormhole_csv(csv_content)

        assert len(result) == 3
        assert result[0] == {'code': 'A009', 'scan_strength': 10.0}
        assert result[2]['scan_strength'] is None

    def test_calculate_checksum(self):
        """Test checksum for change detection."""
        importer = WormholeImporter()
        checksum = importer.calculate_checksum("test content")
        assert len(checksum) == 64  # SHA-256 hex
