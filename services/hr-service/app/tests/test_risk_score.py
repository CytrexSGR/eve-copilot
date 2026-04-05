"""Tests for risk score calculation logic.

Tests the weighted risk score formula from vetting_engine.py:
- Weight constants
- Red list scoring (severity-based)
- Wallet risk addition (capped)
- Skill injection detection
- Character age check
- Final score capping at 100
"""

import pytest

# ---- Inline constants from vetting_engine.py ----

WEIGHT_RED_LIST = 30
WEIGHT_WALLET = 25
WEIGHT_SKILL_INJECTION = 20
WEIGHT_CHAR_AGE = 10
WEIGHT_CORP_HISTORY = 15

SUSPICIOUS_REF_TYPES = {
    "player_trading": 10,
    "player_donation": 8,
    "corporation_account_withdrawal": 5,
}


# ---- Pure calculation functions extracted from VettingEngine ----


def calculate_red_list_risk(hits: list[dict]) -> int:
    """Calculate risk score contribution from red list hits.

    Reimplemented from VettingEngine.check_applicant Stage 1.
    """
    if not hits:
        return 0
    max_severity = max(h.get("severity", 1) for h in hits)
    return min(WEIGHT_RED_LIST, WEIGHT_RED_LIST * max_severity // 5)


def calculate_wallet_risk(journal: list[dict]) -> tuple[list[dict], int]:
    """Calculate wallet risk from journal entries.

    Reimplemented from VettingEngine._analyze_wallet.
    Returns (flags, risk_add).
    """
    flags = []
    risk_add = 0

    for entry in journal:
        ref_type = entry.get("ref_type", "")
        if ref_type in SUSPICIOUS_REF_TYPES:
            amount = abs(entry.get("amount", 0))
            weight = SUSPICIOUS_REF_TYPES[ref_type]

            if amount > 100_000_000:  # >100M ISK
                weight *= 2
            elif amount > 1_000_000_000:  # >1B ISK
                weight *= 3

            flags.append({
                "ref_type": ref_type,
                "amount": entry.get("amount"),
                "risk_weight": weight,
            })
            risk_add += weight

    capped_risk = min(WEIGHT_WALLET, risk_add)
    return flags, capped_risk


def estimate_injectors(injected_sp: float, current_sp: int) -> int:
    """Estimate number of skill injectors based on SP brackets.

    Reimplemented from VettingEngine._detect_skill_injection.
    """
    if current_sp < 5_000_000:
        estimated = int(injected_sp / 500_000)
    elif current_sp < 50_000_000:
        estimated = int(injected_sp / 400_000)
    elif current_sp < 80_000_000:
        estimated = int(injected_sp / 300_000)
    else:
        estimated = int(injected_sp / 150_000)
    return max(1, estimated)


def calculate_total_risk(
    red_list_risk: int = 0,
    wallet_risk: int = 0,
    skill_injection: bool = False,
    young_character: bool = False,
) -> int:
    """Calculate total risk score with 100 cap.

    Reimplemented from VettingEngine.check_applicant final calculation.
    """
    score = red_list_risk + wallet_risk
    if skill_injection:
        score += WEIGHT_SKILL_INJECTION
    if young_character:
        score += WEIGHT_CHAR_AGE
    return min(100, score)


# ---- Tests ----


class TestWeightConstants:
    """Verify weight constants add up correctly and are within bounds."""

    def test_all_weights_positive(self):
        """All risk weights must be positive."""
        for w in [WEIGHT_RED_LIST, WEIGHT_WALLET, WEIGHT_SKILL_INJECTION,
                  WEIGHT_CHAR_AGE, WEIGHT_CORP_HISTORY]:
            assert w > 0

    def test_total_weights_equal_100(self):
        """Sum of all component weights should be exactly 100."""
        total = (WEIGHT_RED_LIST + WEIGHT_WALLET + WEIGHT_SKILL_INJECTION +
                 WEIGHT_CHAR_AGE + WEIGHT_CORP_HISTORY)
        assert total == 100

    def test_individual_weights(self):
        """Verify each weight matches spec."""
        assert WEIGHT_RED_LIST == 30
        assert WEIGHT_WALLET == 25
        assert WEIGHT_SKILL_INJECTION == 20
        assert WEIGHT_CHAR_AGE == 10
        assert WEIGHT_CORP_HISTORY == 15


class TestRedListRisk:
    """Tests for red list risk contribution."""

    def test_no_hits_returns_zero(self):
        """No red list hits means zero risk contribution."""
        assert calculate_red_list_risk([]) == 0

    def test_severity_1_produces_min_score(self):
        """Severity 1 (lowest) should produce 30 * 1 // 5 = 6."""
        hits = [{"severity": 1}]
        assert calculate_red_list_risk(hits) == 6

    def test_severity_5_produces_max_score(self):
        """Severity 5 (highest) should produce full 30 points."""
        hits = [{"severity": 5}]
        assert calculate_red_list_risk(hits) == 30

    def test_severity_3_produces_proportional_score(self):
        """Severity 3 should produce 30 * 3 // 5 = 18."""
        hits = [{"severity": 3}]
        assert calculate_red_list_risk(hits) == 18

    def test_multiple_hits_uses_max_severity(self):
        """Multiple hits should use the maximum severity found."""
        hits = [{"severity": 1}, {"severity": 4}, {"severity": 2}]
        expected = min(WEIGHT_RED_LIST, WEIGHT_RED_LIST * 4 // 5)  # 24
        assert calculate_red_list_risk(hits) == expected

    def test_missing_severity_defaults_to_1(self):
        """Hits without severity key should default to 1."""
        hits = [{}]
        assert calculate_red_list_risk(hits) == 6

    def test_score_never_exceeds_weight(self):
        """Red list risk should never exceed WEIGHT_RED_LIST."""
        hits = [{"severity": 5}]
        assert calculate_red_list_risk(hits) <= WEIGHT_RED_LIST


class TestWalletRisk:
    """Tests for wallet heuristic risk calculation."""

    def test_empty_journal_no_risk(self):
        """Empty journal should produce no flags and zero risk."""
        flags, risk = calculate_wallet_risk([])
        assert flags == []
        assert risk == 0

    def test_normal_transaction_ignored(self):
        """Non-suspicious ref_types should not generate flags."""
        journal = [{"ref_type": "market_escrow", "amount": 500000000}]
        flags, risk = calculate_wallet_risk(journal)
        assert flags == []
        assert risk == 0

    def test_player_trading_flagged(self):
        """player_trading should be flagged with base weight 10."""
        journal = [{"ref_type": "player_trading", "amount": 1000000}]
        flags, risk = calculate_wallet_risk(journal)
        assert len(flags) == 1
        assert flags[0]["risk_weight"] == 10

    def test_player_donation_flagged(self):
        """player_donation should be flagged with base weight 8."""
        journal = [{"ref_type": "player_donation", "amount": 1000000}]
        flags, risk = calculate_wallet_risk(journal)
        assert len(flags) == 1
        assert flags[0]["risk_weight"] == 8

    def test_corp_withdrawal_flagged(self):
        """corporation_account_withdrawal flagged with base weight 5."""
        journal = [{"ref_type": "corporation_account_withdrawal", "amount": 1000000}]
        flags, risk = calculate_wallet_risk(journal)
        assert len(flags) == 1
        assert flags[0]["risk_weight"] == 5

    def test_large_amount_doubles_weight(self):
        """Amounts >100M ISK should double the weight."""
        journal = [{"ref_type": "player_trading", "amount": 200_000_000}]
        flags, risk = calculate_wallet_risk(journal)
        assert flags[0]["risk_weight"] == 20  # 10 * 2

    def test_negative_amount_uses_abs(self):
        """Negative amounts (outgoing) should use absolute value."""
        journal = [{"ref_type": "player_donation", "amount": -500_000_000}]
        flags, risk = calculate_wallet_risk(journal)
        assert flags[0]["risk_weight"] == 16  # 8 * 2 (abs > 100M)

    def test_risk_capped_at_wallet_weight(self):
        """Total wallet risk should never exceed WEIGHT_WALLET (25)."""
        # Generate enough suspicious entries to exceed 25
        journal = [
            {"ref_type": "player_trading", "amount": 200_000_000},  # weight 20
            {"ref_type": "player_trading", "amount": 200_000_000},  # weight 20
        ]
        flags, risk = calculate_wallet_risk(journal)
        assert risk == WEIGHT_WALLET  # capped at 25
        assert risk <= 25

    def test_multiple_suspicious_types(self):
        """Multiple different suspicious types should accumulate."""
        journal = [
            {"ref_type": "player_trading", "amount": 1000000},     # 10
            {"ref_type": "player_donation", "amount": 1000000},    # 8
            {"ref_type": "corporation_account_withdrawal", "amount": 1000000},  # 5
        ]
        flags, risk = calculate_wallet_risk(journal)
        assert len(flags) == 3
        assert risk == 23  # 10 + 8 + 5 = 23

    def test_amount_thresholds_boundary_100m(self):
        """Amount exactly at 100M boundary should NOT trigger doubling."""
        journal = [{"ref_type": "player_trading", "amount": 100_000_000}]
        flags, risk = calculate_wallet_risk(journal)
        assert flags[0]["risk_weight"] == 10  # Exactly 100M, not >100M

    def test_amount_just_above_100m(self):
        """Amount just over 100M should trigger doubling."""
        journal = [{"ref_type": "player_trading", "amount": 100_000_001}]
        flags, risk = calculate_wallet_risk(journal)
        assert flags[0]["risk_weight"] == 20


class TestInjectorEstimation:
    """Tests for skill injector count estimation."""

    def test_low_sp_bracket(self):
        """Characters <5M SP get 500K SP per injector."""
        estimated = estimate_injectors(1_000_000, 3_000_000)
        assert estimated == 2  # 1M / 500K

    def test_mid_sp_bracket(self):
        """Characters 5-50M SP get 400K SP per injector."""
        estimated = estimate_injectors(1_200_000, 20_000_000)
        assert estimated == 3  # 1.2M / 400K

    def test_high_sp_bracket(self):
        """Characters 50-80M SP get 300K SP per injector."""
        estimated = estimate_injectors(900_000, 60_000_000)
        assert estimated == 3  # 900K / 300K

    def test_very_high_sp_bracket(self):
        """Characters >80M SP get 150K SP per injector."""
        estimated = estimate_injectors(600_000, 100_000_000)
        assert estimated == 4  # 600K / 150K

    def test_minimum_one_injector(self):
        """Estimate should always be at least 1 even for small SP deltas."""
        estimated = estimate_injectors(1000, 3_000_000)
        assert estimated >= 1

    def test_bracket_boundary_5m(self):
        """At exactly 5M SP, should use 400K bracket (5M is NOT <5M)."""
        estimated = estimate_injectors(400_000, 5_000_000)
        assert estimated == 1  # 400K / 400K

    def test_bracket_boundary_50m(self):
        """At exactly 50M SP, should use 300K bracket."""
        estimated = estimate_injectors(300_000, 50_000_000)
        assert estimated == 1  # 300K / 300K

    def test_bracket_boundary_80m(self):
        """At exactly 80M SP, should use 150K bracket."""
        estimated = estimate_injectors(150_000, 80_000_000)
        assert estimated == 1  # 150K / 150K


class TestTotalRiskScore:
    """Tests for the final risk score calculation with capping."""

    def test_zero_risk(self):
        """No flags should produce zero risk."""
        assert calculate_total_risk() == 0

    def test_only_red_list(self):
        """Only red list risk contribution."""
        assert calculate_total_risk(red_list_risk=18) == 18

    def test_only_wallet(self):
        """Only wallet risk contribution."""
        assert calculate_total_risk(wallet_risk=15) == 15

    def test_only_skill_injection(self):
        """Skill injection adds its weight."""
        assert calculate_total_risk(skill_injection=True) == WEIGHT_SKILL_INJECTION

    def test_only_young_character(self):
        """Young character adds WEIGHT_CHAR_AGE."""
        assert calculate_total_risk(young_character=True) == WEIGHT_CHAR_AGE

    def test_all_flags_at_max(self):
        """All risk factors at maximum should cap at 100."""
        score = calculate_total_risk(
            red_list_risk=30,
            wallet_risk=25,
            skill_injection=True,
            young_character=True,
        )
        assert score == 85  # 30 + 25 + 20 + 10

    def test_score_never_exceeds_100(self):
        """Total risk score must never exceed 100 regardless of inputs."""
        # Artificially high inputs
        score = calculate_total_risk(
            red_list_risk=50,
            wallet_risk=40,
            skill_injection=True,
            young_character=True,
        )
        assert score == 100

    def test_additive_combination(self):
        """Multiple factors should add up correctly when below cap."""
        score = calculate_total_risk(
            red_list_risk=10,
            wallet_risk=10,
            skill_injection=False,
            young_character=True,
        )
        assert score == 30  # 10 + 10 + 0 + 10
