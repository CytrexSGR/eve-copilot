"""Tests for DecimalEncoder and cache serialization edge cases."""

import json
import pytest
from decimal import Decimal
from app.utils.cache import _DecimalEncoder


class TestDecimalEncoder:
    def test_decimal_to_float(self):
        data = {"value": Decimal("123.45")}
        result = json.dumps(data, cls=_DecimalEncoder)
        assert '"value": 123.45' in result

    def test_decimal_integer(self):
        data = {"count": Decimal("42")}
        result = json.dumps(data, cls=_DecimalEncoder)
        parsed = json.loads(result)
        assert parsed["count"] == 42.0

    def test_decimal_zero(self):
        data = {"zero": Decimal("0")}
        result = json.dumps(data, cls=_DecimalEncoder)
        parsed = json.loads(result)
        assert parsed["zero"] == 0.0

    def test_decimal_negative(self):
        data = {"loss": Decimal("-999.99")}
        result = json.dumps(data, cls=_DecimalEncoder)
        parsed = json.loads(result)
        assert parsed["loss"] == pytest.approx(-999.99)

    def test_decimal_very_large(self):
        data = {"isk": Decimal("1234567890123.456")}
        result = json.dumps(data, cls=_DecimalEncoder)
        parsed = json.loads(result)
        assert parsed["isk"] == pytest.approx(1234567890123.456)

    def test_mixed_types(self):
        data = {
            "kills": 100,
            "efficiency": Decimal("78.5"),
            "name": "Test Corp",
            "values": [Decimal("1.1"), Decimal("2.2")],
        }
        result = json.dumps(data, cls=_DecimalEncoder)
        parsed = json.loads(result)
        assert parsed["kills"] == 100
        assert parsed["efficiency"] == 78.5
        assert parsed["name"] == "Test Corp"
        assert parsed["values"] == [1.1, 2.2]

    def test_non_decimal_raises_type_error(self):
        """Non-serializable types still raise TypeError."""
        data = {"obj": object()}
        with pytest.raises(TypeError):
            json.dumps(data, cls=_DecimalEncoder)

    def test_nested_decimals(self):
        data = {"outer": {"inner": Decimal("3.14")}}
        result = json.dumps(data, cls=_DecimalEncoder)
        parsed = json.loads(result)
        assert parsed["outer"]["inner"] == pytest.approx(3.14)
