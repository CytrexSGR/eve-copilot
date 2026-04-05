"""Tests for skill_planner_service.py and skill_analysis_service.py pure functions.

Covers: SP calculation, training time, format_duration, optimal attributes,
        remap points, AnalysisType enum, prompt generation.
"""

import math
import pytest

from app.services.skill_planner_service import (
    sp_for_level,
    sp_between_levels,
    sp_per_minute,
    training_seconds,
    format_duration,
    calculate_optimal_attributes,
    find_remap_points,
    SkillItem,
    ATTRIBUTES,
    MIN_ATTR,
    MAX_ATTR,
    TOTAL_POINTS,
)
from app.services.skill_analysis_service import (
    AnalysisType,
    SkillAnalysisService,
)
from app.services.skill_prerequisites_service import SP_PER_LEVEL


# ---------------------------------------------------------------------------
# sp_for_level
# ---------------------------------------------------------------------------

class TestSPForLevel:
    """Test SP calculation for reaching a skill level."""

    def test_level_zero_returns_zero(self):
        assert sp_for_level(1, 0) == 0

    def test_negative_level_returns_zero(self):
        assert sp_for_level(1, -1) == 0

    @pytest.mark.parametrize("level,expected_approx", [
        (1, 250),
        (2, 1414),
        (3, 8000),
        (4, 45254),
        (5, 256000),
    ])
    def test_rank_1_levels(self, level, expected_approx):
        """Rank 1 SP per level matches EVE formula: 250 * sqrt(32)^(L-1)."""
        result = sp_for_level(1, level)
        # Allow small rounding difference due to int()
        assert abs(result - expected_approx) <= 2

    def test_rank_multiplier(self):
        """Higher rank multiplies SP proportionally."""
        rank1 = sp_for_level(1, 3)
        rank5 = sp_for_level(5, 3)
        assert rank5 == rank1 * 5


# ---------------------------------------------------------------------------
# sp_between_levels
# ---------------------------------------------------------------------------

class TestSPBetweenLevels:
    """Test SP difference between two levels."""

    def test_same_level_returns_zero(self):
        assert sp_between_levels(1, 3, 3) == 0

    def test_level_0_to_1(self):
        result = sp_between_levels(1, 0, 1)
        assert result == sp_for_level(1, 1) - sp_for_level(1, 0)
        assert result == 250

    def test_level_4_to_5_rank_1(self):
        """L4->L5 requires the most SP."""
        result = sp_between_levels(1, 4, 5)
        expected = sp_for_level(1, 5) - sp_for_level(1, 4)
        assert result == expected
        assert result > 200000  # ~210,746 SP for rank 1

    def test_multi_level_jump(self):
        """0->5 equals sum of individual level jumps."""
        total = sp_between_levels(3, 0, 5)
        incremental = sum(sp_between_levels(3, i, i + 1) for i in range(5))
        assert total == incremental


# ---------------------------------------------------------------------------
# sp_per_minute
# ---------------------------------------------------------------------------

class TestSPPerMinute:
    """Test SP rate calculation."""

    def test_basic_rate(self):
        # primary + secondary/2
        assert sp_per_minute(20, 20) == 30.0

    def test_high_attributes(self):
        assert sp_per_minute(27, 21) == 37.5

    def test_minimum_attributes(self):
        assert sp_per_minute(17, 17) == 25.5


# ---------------------------------------------------------------------------
# training_seconds
# ---------------------------------------------------------------------------

class TestTrainingSeconds:
    """Test training time calculation."""

    def test_zero_sp_returns_zero(self):
        assert training_seconds(0, 20, 20) == 0

    def test_basic_calculation(self):
        """250 SP at 30 SP/min = 8.33 min = 500 sec."""
        result = training_seconds(250, 20, 20)
        assert result == 500  # (250/30) * 60 = 500

    def test_zero_attributes_returns_zero(self):
        """Zero primary means spm=0, should not divide by zero."""
        assert training_seconds(1000, 0, 0) == 0

    def test_higher_attributes_faster(self):
        """Higher attributes -> shorter training time."""
        slow = training_seconds(10000, 17, 17)
        fast = training_seconds(10000, 27, 27)
        assert fast < slow


# ---------------------------------------------------------------------------
# format_duration
# ---------------------------------------------------------------------------

class TestFormatDuration:
    """Test human-readable duration formatting."""

    @pytest.mark.parametrize("seconds,expected", [
        (0, "0s"),
        (-5, "0s"),
        (60, "1m"),
        (300, "5m"),
        (3600, "1h 0m"),
        (3660, "1h 1m"),
        (7200, "2h 0m"),
        (86400, "1d 0h"),
        (90000, "1d 1h"),
        (172800, "2d 0h"),
        (180000, "2d 2h"),  # 180000 = 2*86400 + 7200 = 2d 2h
    ])
    def test_format_cases(self, seconds, expected):
        assert format_duration(seconds) == expected


# ---------------------------------------------------------------------------
# calculate_optimal_attributes
# ---------------------------------------------------------------------------

class TestCalculateOptimalAttributes:
    """Test optimal attribute distribution for skill plans."""

    def test_empty_skills_returns_default(self):
        result = calculate_optimal_attributes([])
        assert sum(result.values()) == TOTAL_POINTS
        for attr in ATTRIBUTES:
            assert attr in result

    def test_sum_equals_total_points(self):
        """Allocated points always sum to TOTAL_POINTS (99)."""
        skills = [
            SkillItem(1, 100, "Gunnery", 2, 0, 5, "perception", "willpower"),
            SkillItem(2, 200, "Engineering", 3, 0, 4, "intelligence", "memory"),
        ]
        result = calculate_optimal_attributes(skills)
        assert sum(result.values()) == TOTAL_POINTS

    def test_all_attributes_at_least_minimum(self):
        """No attribute goes below MIN_ATTR (17)."""
        skills = [
            SkillItem(1, 100, "Gunnery", 5, 0, 5, "perception", "willpower"),
        ]
        result = calculate_optimal_attributes(skills)
        for attr in ATTRIBUTES:
            assert result[attr] >= MIN_ATTR

    def test_no_attribute_exceeds_maximum(self):
        """No attribute exceeds MAX_ATTR (27)."""
        skills = [
            SkillItem(1, 100, "Gunnery", 5, 0, 5, "perception", "perception"),
        ]
        result = calculate_optimal_attributes(skills)
        for attr in ATTRIBUTES:
            assert result[attr] <= MAX_ATTR

    def test_perception_favored_for_gunnery(self):
        """Perception-heavy plan gets highest perception allocation."""
        skills = [
            SkillItem(1, 100, "SmallHybrid", 3, 0, 5, "perception", "willpower"),
            SkillItem(2, 101, "MedHybrid", 3, 0, 5, "perception", "willpower"),
            SkillItem(3, 102, "LargeHybrid", 5, 0, 5, "perception", "willpower"),
        ]
        result = calculate_optimal_attributes(skills)
        assert result["perception"] >= result["willpower"]
        assert result["perception"] >= result["intelligence"]


# ---------------------------------------------------------------------------
# find_remap_points
# ---------------------------------------------------------------------------

class TestFindRemapPoints:
    """Test remap suggestion algorithm."""

    def test_empty_plan_no_suggestions(self):
        result = find_remap_points([], {"perception": 20, "memory": 20, "willpower": 20, "intelligence": 20, "charisma": 19}, {})
        assert result == []

    def test_single_skill_no_suggestion(self):
        """Single skill plan never suggests a remap."""
        items = [
            SkillItem(1, 100, "Gunnery", 1, 0, 5, "perception", "willpower"),
        ]
        attrs = {a: 20 for a in ATTRIBUTES}
        attrs["charisma"] = 19
        result = find_remap_points(items, attrs, {})
        assert result == []

    def test_no_remap_when_attributes_match(self):
        """When current attributes already optimal, no remap needed."""
        items = [
            SkillItem(1, 100, "Gunnery", 1, 0, 5, "perception", "willpower"),
            SkillItem(2, 101, "Gunnery2", 1, 0, 5, "perception", "willpower"),
        ]
        optimal = calculate_optimal_attributes(items)
        result = find_remap_points(items, optimal, {})
        assert result == []


# ---------------------------------------------------------------------------
# AnalysisType enum
# ---------------------------------------------------------------------------

class TestAnalysisType:
    """Test AnalysisType enum values."""

    def test_all_types_are_strings(self):
        for t in AnalysisType:
            assert isinstance(t.value, str)

    @pytest.mark.parametrize("member,value", [
        (AnalysisType.INDIVIDUAL_ASSESSMENT, "individual_assessment"),
        (AnalysisType.TEAM_COMPOSITION, "team_composition"),
        (AnalysisType.TRAINING_PRIORITIES, "training_priorities"),
        (AnalysisType.ROLE_OPTIMIZATION, "role_optimization"),
        (AnalysisType.GAP_ANALYSIS, "gap_analysis"),
        (AnalysisType.WEEKLY_SUMMARY, "weekly_summary"),
        (AnalysisType.MONTHLY_REVIEW, "monthly_review"),
    ])
    def test_enum_values(self, member, value):
        assert member.value == value

    def test_enum_count(self):
        assert len(AnalysisType) == 7


# ---------------------------------------------------------------------------
# generate_analysis_prompt
# ---------------------------------------------------------------------------

class TestGenerateAnalysisPrompt:
    """Test prompt generation for skill analysis."""

    def test_individual_assessment_prompt(self):
        service = SkillAnalysisService()
        prompt = service.generate_analysis_prompt(
            AnalysisType.INDIVIDUAL_ASSESSMENT,
            {"characters": [{"name": "Cytrex"}]}
        )
        assert "Charakter-Skill-Daten" in prompt
        assert "Cytrex" in prompt

    def test_team_composition_prompt(self):
        service = SkillAnalysisService()
        prompt = service.generate_analysis_prompt(
            AnalysisType.TEAM_COMPOSITION,
            {"team_size": 4}
        )
        assert "Team-Zusammensetzung" in prompt

    def test_training_priorities_prompt(self):
        service = SkillAnalysisService()
        prompt = service.generate_analysis_prompt(
            AnalysisType.TRAINING_PRIORITIES,
            {"skill_gaps": []}
        )
        assert "Trainingsempfehlungen" in prompt

    def test_gap_analysis_prompt(self):
        service = SkillAnalysisService()
        prompt = service.generate_analysis_prompt(
            AnalysisType.GAP_ANALYSIS,
            {"gaps": []}
        )
        assert "Skill-L\u00fccken" in prompt


# ---------------------------------------------------------------------------
# SP_PER_LEVEL constants (skill_prerequisites_service)
# ---------------------------------------------------------------------------

class TestSPPerLevelConstants:
    """Verify SP_PER_LEVEL constants match EVE formula."""

    @pytest.mark.parametrize("level,expected", [
        (1, 250),
        (2, 1414),
        (3, 8000),
        (4, 45255),
        (5, 256000),
    ])
    def test_sp_per_level_values(self, level, expected):
        assert SP_PER_LEVEL[level] == expected

    def test_sp_increases_exponentially(self):
        """Each level requires more SP than the previous."""
        levels = sorted(SP_PER_LEVEL.keys())
        for i in range(1, len(levels)):
            assert SP_PER_LEVEL[levels[i]] > SP_PER_LEVEL[levels[i - 1]]
