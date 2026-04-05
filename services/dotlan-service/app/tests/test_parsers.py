"""Tests for dotlan-service HTML/JS parsers and data transformation functions.

Covers:
- BaseScraper.parse_dotline_chart() - JavaScript chart data extraction
- BaseScraper.parse_label_to_timestamp() - DOTLAN label to datetime
- SovereigntyScraper._parse_change_timestamp() - Multi-format timestamp parsing
- TokenBucketRateLimiter - Token bucket initialization and state
- DotlanConfig - Configuration property parsing
- ActivityScraper constants - CHART_TO_COLUMN mapping validation
"""

import pytest
from datetime import datetime


# ---------------------------------------------------------------------------
# parse_dotline_chart — extract data from DOTLAN's JS chart initialization
# ---------------------------------------------------------------------------

class TestParseDotlineChart:
    """Test the parse_dotline_chart method of BaseScraper.

    This method is the core of DOTLAN scraping — it extracts chart data
    from JavaScript object literals embedded in HTML. DOTLAN uses unquoted
    keys (not valid JSON), so the parser must fix them before parsing.
    """

    @pytest.fixture(autouse=True)
    def _setup(self):
        """Create a minimal BaseScraper with parse_dotline_chart accessible.

        We import the method directly to avoid needing the full infrastructure
        (DB, rate limiter, HTTP client) that BaseScraper.__init__ requires.
        """
        from app.services.scraper_base import BaseScraper
        # Bypass __init__ to avoid infrastructure dependencies
        self.scraper = object.__new__(BaseScraper)

    def _make_html(self, chart_id, labels, datasets):
        """Build a minimal DOTLAN-style HTML page with embedded chart JS."""
        labels_str = ", ".join(f'"{l}"' for l in labels)
        # Build datasets array (DOTLAN uses unquoted keys inside datasets too,
        # but dataset objects use quoted keys for "label" and "data")
        ds_parts = []
        for ds in datasets:
            data_str = ", ".join(
                "null" if v is None else f'"{v}"' if isinstance(v, str) else str(v)
                for v in ds["data"]
            )
            ds_parts.append(f'{{"label":"{ds["label"]}","data":[{data_str}]}}')
        datasets_str = ", ".join(ds_parts)

        return f'''<html><body>
<script>
window.chart_{chart_id} = new dotLineChart(
\t"#chart_{chart_id}",
\t{{
\t\tlabels: [{labels_str}],
\t\tdatasets: [{datasets_str}]
\t}}
);
</script>
</body></html>'''

    def test_basic_integer_values(self):
        """Parse chart with simple string-encoded integer values."""
        html = self._make_html(
            "jumps",
            ["2026-01-28 12", "2026-01-28 13", "2026-01-28 14"],
            [{"label": "Jumps", "data": ["4", "17", "23"]}],
        )
        result = self.scraper.parse_dotline_chart(html, "jumps")
        assert len(result) == 3
        assert result[0] == ("2026-01-28 12", 4)
        assert result[1] == ("2026-01-28 13", 17)
        assert result[2] == ("2026-01-28 14", 23)

    def test_null_values_become_zero(self):
        """Null values in chart data should be parsed as 0."""
        html = self._make_html(
            "npc",
            ["2026-01-28 12", "2026-01-28 13"],
            [{"label": "NPC Kills", "data": [None, "5"]}],
        )
        result = self.scraper.parse_dotline_chart(html, "npc")
        assert result[0] == ("2026-01-28 12", 0)
        assert result[1] == ("2026-01-28 13", 5)

    def test_empty_string_values_become_zero(self):
        """Empty string values in chart data should be parsed as 0."""
        html = self._make_html(
            "kills",
            ["2026-01-28 12"],
            [{"label": "Kills", "data": [""]}],
        )
        result = self.scraper.parse_dotline_chart(html, "kills")
        assert result[0] == ("2026-01-28 12", 0)

    def test_float_values_preserved(self):
        """ADM values come as floats like 4.5 and should be preserved."""
        html = self._make_html(
            "adm",
            ["2026-01-28 12", "2026-01-28 13"],
            [{"label": "ADM", "data": ["4.5", "3.7"]}],
        )
        result = self.scraper.parse_dotline_chart(html, "adm")
        assert result[0] == ("2026-01-28 12", 4.5)
        assert result[1] == ("2026-01-28 13", 3.7)

    def test_whole_float_values_become_int(self):
        """Float values like 5.0 should become int 5."""
        html = self._make_html(
            "jumps",
            ["2026-01-28 12"],
            [{"label": "Jumps", "data": ["5.0"]}],
        )
        result = self.scraper.parse_dotline_chart(html, "jumps")
        assert result[0] == ("2026-01-28 12", 5)
        assert isinstance(result[0][1], int)

    def test_chart_not_found_returns_empty(self):
        """If the chart ID is not present in the HTML, return empty list."""
        html = "<html><body>No charts here</body></html>"
        result = self.scraper.parse_dotline_chart(html, "nonexistent")
        assert result == []

    def test_empty_datasets_returns_empty(self):
        """If datasets array is empty, return empty list."""
        html = '''<html><script>
window.chart_test = new dotLineChart(
\t"#chart_test",
\t{
\t\tlabels: ["2026-01-28 12"],
\t\tdatasets: []
\t}
);
</script></html>'''
        result = self.scraper.parse_dotline_chart(html, "test")
        assert result == []

    def test_numeric_int_values(self):
        """Handle native numeric (non-string) values in chart data."""
        # Build HTML with native numbers (not string-quoted)
        html = '''<html><script>
window.chart_npc = new dotLineChart(
\t"#chart_npc",
\t{
\t\tlabels: ["2026-01-28 12", "2026-01-28 13"],
\t\tdatasets: [{"label":"NPC","data":[42, 100]}]
\t}
);
</script></html>'''
        result = self.scraper.parse_dotline_chart(html, "npc")
        assert result[0] == ("2026-01-28 12", 42)
        assert result[1] == ("2026-01-28 13", 100)

    def test_multiple_labels_and_values_aligned(self):
        """Labels and values arrays must be aligned (zip behavior)."""
        html = self._make_html(
            "pods",
            ["2026-01-28 12", "2026-01-28 13", "2026-01-28 14", "2026-01-28 15"],
            [{"label": "Pods", "data": ["1", "0", "3"]}],
        )
        # zip stops at shortest, so 4 labels + 3 values = 3 results
        result = self.scraper.parse_dotline_chart(html, "pods")
        assert len(result) == 3

    @pytest.mark.parametrize("bad_val,expected", [
        ("abc", 0),
        ("null", 0),
        ("", 0),
    ])
    def test_invalid_string_values_become_zero(self, bad_val, expected):
        """Non-numeric string values should be converted to 0."""
        html = self._make_html(
            "jumps",
            ["2026-01-28 12"],
            [{"label": "Jumps", "data": [bad_val]}],
        )
        result = self.scraper.parse_dotline_chart(html, "jumps")
        assert result[0][1] == expected

    def test_fallback_chart_id_marker(self):
        """Parser should find chart by #chart_ID even without exact whitespace match."""
        # Use non-standard whitespace (spaces instead of tabs)
        html = '''<html><script>
window.chart_jumps = new dotLineChart(
  "#chart_jumps",
  {
    labels: ["2026-01-28 12"],
    datasets: [{"label":"Jumps","data":["7"]}]
  }
);
</script></html>'''
        result = self.scraper.parse_dotline_chart(html, "jumps")
        assert len(result) == 1
        assert result[0] == ("2026-01-28 12", 7)


# ---------------------------------------------------------------------------
# parse_label_to_timestamp — convert DOTLAN chart labels to datetime
# ---------------------------------------------------------------------------

class TestParseLabelToTimestamp:
    """Test BaseScraper.parse_label_to_timestamp static method."""

    @pytest.mark.parametrize("label,expected", [
        ("2026-01-28 12", datetime(2026, 1, 28, 12, 0)),
        ("2026-12-31 23", datetime(2026, 12, 31, 23, 0)),
        ("2025-06-15 00", datetime(2025, 6, 15, 0, 0)),
        (" 2026-01-28 12 ", datetime(2026, 1, 28, 12, 0)),  # leading/trailing spaces
    ])
    def test_valid_labels(self, label, expected):
        from app.services.scraper_base import BaseScraper
        assert BaseScraper.parse_label_to_timestamp(label) == expected

    @pytest.mark.parametrize("bad_label", [
        "2026-01-28",       # missing hour
        "28-01-2026 12",    # wrong date format
        "not-a-date",
        "",
    ])
    def test_invalid_labels_raise(self, bad_label):
        from app.services.scraper_base import BaseScraper
        with pytest.raises(ValueError):
            BaseScraper.parse_label_to_timestamp(bad_label)


# ---------------------------------------------------------------------------
# _parse_change_timestamp — multi-format timestamp parser
# ---------------------------------------------------------------------------

class TestParseChangeTimestamp:
    """Test SovereigntyScraper._parse_change_timestamp method."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        from app.services.sovereignty_scraper import SovereigntyScraper
        self.scraper = object.__new__(SovereigntyScraper)

    @pytest.mark.parametrize("text,expected_iso", [
        ("2026-01-28 14:30", "2026-01-28T14:30:00"),
        ("2026-01-28", "2026-01-28T00:00:00"),
        ("01/28/2026 14:30", "2026-01-28T14:30:00"),
        ("01/28/2026", "2026-01-28T00:00:00"),
        (" 2026-01-28 14:30 ", "2026-01-28T14:30:00"),  # whitespace
    ])
    def test_valid_timestamps(self, text, expected_iso):
        result = self.scraper._parse_change_timestamp(text)
        assert result == expected_iso

    @pytest.mark.parametrize("bad_text", [
        "not-a-date",
        "28.01.2026",
        "",
        "yesterday",
    ])
    def test_invalid_timestamps_return_none(self, bad_text):
        result = self.scraper._parse_change_timestamp(bad_text)
        assert result is None


# ---------------------------------------------------------------------------
# TokenBucketRateLimiter — initialization and state
# ---------------------------------------------------------------------------

class TestTokenBucketRateLimiter:
    """Test TokenBucketRateLimiter initialization and properties."""

    def test_default_init(self):
        from app.services.rate_limiter import TokenBucketRateLimiter
        limiter = TokenBucketRateLimiter()
        assert limiter.rate == 1.0
        assert limiter.burst == 3
        assert limiter.tokens == 3.0
        assert limiter.total_waits == 0

    def test_custom_init(self):
        from app.services.rate_limiter import TokenBucketRateLimiter
        limiter = TokenBucketRateLimiter(rate=2.0, burst=5)
        assert limiter.rate == 2.0
        assert limiter.burst == 5
        assert limiter.tokens == 5.0

    def test_initial_tokens_equals_burst(self):
        """Initial token count should equal burst capacity."""
        from app.services.rate_limiter import TokenBucketRateLimiter
        for burst in [1, 5, 10, 100]:
            limiter = TokenBucketRateLimiter(burst=burst)
            assert limiter.tokens == float(burst)

    def test_total_waits_starts_at_zero(self):
        from app.services.rate_limiter import TokenBucketRateLimiter
        limiter = TokenBucketRateLimiter()
        assert limiter.total_waits == 0


# ---------------------------------------------------------------------------
# DotlanConfig — configuration property parsing
# ---------------------------------------------------------------------------

class TestDotlanConfig:
    """Test DotlanConfig computed properties."""

    def test_cors_origin_list_wildcard(self):
        from app.config import DotlanConfig
        config = DotlanConfig(cors_origins="*")
        assert config.cors_origin_list == ["*"]

    def test_cors_origin_list_multiple(self):
        from app.config import DotlanConfig
        config = DotlanConfig(cors_origins="http://localhost:3000, http://localhost:5173")
        assert config.cors_origin_list == ["http://localhost:3000", "http://localhost:5173"]

    def test_cors_origin_list_empty_entries_filtered(self):
        from app.config import DotlanConfig
        config = DotlanConfig(cors_origins="http://localhost:3000, , ")
        assert config.cors_origin_list == ["http://localhost:3000"]

    def test_region_filter_all(self):
        from app.config import DotlanConfig
        config = DotlanConfig(dotlan_scrape_regions="all")
        assert config.region_filter == []

    def test_region_filter_specific(self):
        from app.config import DotlanConfig
        config = DotlanConfig(dotlan_scrape_regions="Delve, Querious, Period Basis")
        assert config.region_filter == ["Delve", "Querious", "Period Basis"]

    def test_region_filter_empty_entries_filtered(self):
        from app.config import DotlanConfig
        config = DotlanConfig(dotlan_scrape_regions="Delve, , ")
        assert config.region_filter == ["Delve"]


# ---------------------------------------------------------------------------
# ActivityScraper constants — mapping validation
# ---------------------------------------------------------------------------

class TestActivityScraperConstants:
    """Test ActivityScraper constant mappings."""

    def test_chart_to_column_mapping(self):
        from app.services.activity_scraper import ActivityScraper
        expected = {
            "jumps": "jumps",
            "npc": "npc_kills",
            "kills": "ship_kills",
            "pods": "pod_kills",
        }
        assert ActivityScraper.CHART_TO_COLUMN == expected

    def test_charts_list(self):
        from app.services.activity_scraper import ActivityScraper
        assert ActivityScraper.CHARTS == ["jumps", "npc", "kills", "pods"]

    def test_all_charts_have_column_mapping(self):
        """Every chart ID in CHARTS must have a corresponding column mapping."""
        from app.services.activity_scraper import ActivityScraper
        for chart_id in ActivityScraper.CHARTS:
            assert chart_id in ActivityScraper.CHART_TO_COLUMN

    def test_scraper_name(self):
        from app.services.activity_scraper import ActivityScraper
        assert ActivityScraper.SCRAPER_NAME == "activity"


# ---------------------------------------------------------------------------
# Alliance scraper HTML table parsing (extracted logic)
# ---------------------------------------------------------------------------

class TestAllianceHtmlParsing:
    """Test alliance ranking HTML parsing with BeautifulSoup.

    These tests simulate the core parsing logic from AllianceScraper.scrape_rankings
    using sample HTML fragments.
    """

    def _parse_alliance_row(self, html_row):
        """Extract alliance data from a table row (mirrors scraper logic)."""
        import re
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(f"<table><tr>{html_row}</tr></table>", "html.parser")
        row = soup.find("tr")
        cells = row.find_all("td")
        if len(cells) < 4:
            return None

        alliance_link = row.find("a", href=re.compile(r"^/alliance/[^/]+$"))
        if not alliance_link:
            return None

        href = alliance_link.get("href", "")
        alliance_slug = href.replace("/alliance/", "").strip()
        alliance_name = alliance_link.get_text(strip=True)

        if not alliance_name or not alliance_slug:
            return None

        numbers = []
        for cell in cells:
            text = cell.get_text(strip=True).replace(",", "")
            if text.isdigit():
                numbers.append(int(text))

        return {
            "alliance_name": alliance_name,
            "alliance_slug": alliance_slug,
            "systems_count": numbers[0] if len(numbers) >= 1 else 0,
            "member_count": numbers[1] if len(numbers) >= 2 else 0,
            "corp_count": numbers[2] if len(numbers) >= 3 else 0,
        }

    def test_parse_standard_alliance_row(self):
        html = '''
        <td>1</td>
        <td><a href="/alliance/Fraternity.">Fraternity.</a></td>
        <td>156</td>
        <td>23,456</td>
        <td>89</td>
        '''
        result = self._parse_alliance_row(html)
        assert result is not None
        assert result["alliance_name"] == "Fraternity."
        assert result["alliance_slug"] == "Fraternity."
        assert result["systems_count"] == 1  # rank number parsed as first int
        assert result["member_count"] == 156

    def test_parse_row_with_underscore_slug(self):
        html = '''
        <td>5</td>
        <td><a href="/alliance/The_Initiative.">The Initiative.</a></td>
        <td>45</td>
        <td>5,678</td>
        <td>34</td>
        '''
        result = self._parse_alliance_row(html)
        assert result is not None
        assert result["alliance_slug"] == "The_Initiative."
        assert result["alliance_name"] == "The Initiative."

    def test_parse_row_too_few_cells(self):
        html = '''
        <td>1</td>
        <td><a href="/alliance/Test">Test</a></td>
        '''
        result = self._parse_alliance_row(html)
        assert result is None

    def test_parse_row_no_alliance_link(self):
        html = '''
        <td>1</td>
        <td>Just text</td>
        <td>100</td>
        <td>200</td>
        '''
        result = self._parse_alliance_row(html)
        assert result is None


# ---------------------------------------------------------------------------
# Sovereignty campaign HTML parsing (extracted logic)
# ---------------------------------------------------------------------------

class TestSovereigntyCampaignParsing:
    """Test sovereignty campaign HTML parsing with BeautifulSoup."""

    def _extract_campaign_id(self, href):
        """Extract campaign ID from a link href."""
        import re
        match = re.search(r"/sovereignty/campaign/(\d+)", href)
        return int(match.group(1)) if match else None

    def _extract_structure_type(self, cells_text):
        """Extract structure type from cell texts."""
        for text in cells_text:
            if text in ("IHUB", "TCU", "STATION"):
                return text
        return "IHUB"

    def _extract_score(self, text):
        """Extract score percentage from text like '81%'."""
        import re
        match = re.search(r"(\d+)%", text)
        if match:
            return float(match.group(1)) / 100.0
        return None

    @pytest.mark.parametrize("href,expected", [
        ("/sovereignty/campaign/12345", 12345),
        ("/sovereignty/campaign/1", 1),
        ("/sovereignty/campaign/999999", 999999),
    ])
    def test_extract_campaign_id(self, href, expected):
        assert self._extract_campaign_id(href) == expected

    def test_extract_campaign_id_invalid(self):
        assert self._extract_campaign_id("/alliance/test") is None

    @pytest.mark.parametrize("cells,expected", [
        (["2026-01-28", "Delve", "1DQ1-A", "IHUB", "Goonswarm"], "IHUB"),
        (["2026-01-28", "Delve", "1DQ1-A", "TCU", "Goonswarm"], "TCU"),
        (["2026-01-28", "Delve", "1DQ1-A", "STATION", "Goonswarm"], "STATION"),
        (["2026-01-28", "Delve", "1DQ1-A", "Something", "Goonswarm"], "IHUB"),
    ])
    def test_extract_structure_type(self, cells, expected):
        assert self._extract_structure_type(cells) == expected

    @pytest.mark.parametrize("text,expected", [
        ("81%", 0.81),
        ("100%", 1.0),
        ("0%", 0.0),
        ("55%", 0.55),
        ("no score", None),
        ("", None),
    ])
    def test_extract_score(self, text, expected):
        result = self._extract_score(text)
        if expected is None:
            assert result is None
        else:
            assert abs(result - expected) < 0.001


# ---------------------------------------------------------------------------
# Sovereignty change HTML parsing (extracted logic)
# ---------------------------------------------------------------------------

class TestSovereigntyChangeParsing:
    """Test sovereignty change row parsing with BeautifulSoup."""

    def _parse_change_row(self, html_row):
        """Parse a sovereignty change table row (mirrors scraper logic)."""
        import re
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(f"<table><tr>{html_row}</tr></table>", "html.parser")
        row = soup.find("tr")
        cells = row.find_all("td")
        if len(cells) < 4:
            return None

        system_link = row.find("a", href=re.compile(r"/system/"))
        if not system_link:
            return None

        system_name = system_link.get_text(strip=True)

        region_link = row.find("a", href=re.compile(r"/map/"))
        region_name = region_link.get_text(strip=True) if region_link else None

        change_type = "IHUB"
        for cell in cells:
            text = cell.get_text(strip=True)
            if text in ("IHUB", "TCU"):
                change_type = text
                break

        alliance_links = row.find_all("a", href=re.compile(r"/alliance/"))
        old_alliance = alliance_links[0].get_text(strip=True) if len(alliance_links) >= 1 else None
        new_alliance = alliance_links[1].get_text(strip=True) if len(alliance_links) >= 2 else None

        return {
            "system_name": system_name,
            "region_name": region_name,
            "change_type": change_type,
            "old_alliance": old_alliance,
            "new_alliance": new_alliance,
        }

    def test_parse_standard_change_row(self):
        html = '''
        <td>2026-01-28 14:30</td>
        <td><a href="/map/Delve">Delve</a></td>
        <td><a href="/system/1DQ1-A">1DQ1-A</a></td>
        <td>IHUB</td>
        <td><a href="/alliance/OldAlliance">OldAlliance</a></td>
        <td><a href="/alliance/NewAlliance">NewAlliance</a></td>
        '''
        result = self._parse_change_row(html)
        assert result is not None
        assert result["system_name"] == "1DQ1-A"
        assert result["region_name"] == "Delve"
        assert result["change_type"] == "IHUB"
        assert result["old_alliance"] == "OldAlliance"
        assert result["new_alliance"] == "NewAlliance"

    def test_parse_tcu_change(self):
        html = '''
        <td>2026-01-28</td>
        <td><a href="/map/Querious">Querious</a></td>
        <td><a href="/system/49-U6U">49-U6U</a></td>
        <td>TCU</td>
        <td><a href="/alliance/TestAlliance">TestAlliance</a></td>
        '''
        result = self._parse_change_row(html)
        assert result is not None
        assert result["change_type"] == "TCU"
        assert result["old_alliance"] == "TestAlliance"
        assert result["new_alliance"] is None

    def test_parse_row_no_system_link(self):
        html = '''
        <td>2026-01-28</td>
        <td>Delve</td>
        <td>Some text</td>
        <td>IHUB</td>
        '''
        result = self._parse_change_row(html)
        assert result is None

    def test_parse_row_too_few_cells(self):
        html = '''
        <td>2026-01-28</td>
        <td><a href="/system/Test">Test</a></td>
        '''
        result = self._parse_change_row(html)
        assert result is None
