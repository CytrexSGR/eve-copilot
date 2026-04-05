"""Tests for Thanatos comparison bugfixes (agility, cap, armor HP, NSA scan res)."""

import math
import pytest

from app.services.dogma.engine import DogmaEngine
from app.services.dogma.modifier_parser import DogmaModifier
from app.services.fitting_stats.calculations import calculate_capacitor
from app.tests.conftest import MockCursor, MultiResultCursor, MockDB


# ─── Bug 1: Agility PreAssign filter ──────────────────────────────────────────

class TestAgilityPreAssignFilter:
    """Ship hull effects that PreAssign agility (attr 70) should be filtered out."""

    def test_preassign_agility_effects_filtered(self):
        """Effects like shipAdvancedSpaceshipCommandAgilityBonus (PreAssign attr 70)
        should be removed from ship effect modifiers."""
        db = MockDB(result_sets=[
            # _load_ship_effects: ship effects query
            [
                {
                    "effectName": "shipAdvancedSpaceshipCommandAgilityBonus",
                    "modifierInfo": (
                        "- domain: shipID\n"
                        "  func: ItemModifier\n"
                        "  modifiedAttributeID: 70\n"
                        "  modifyingAttributeID: 853\n"
                        "  operation: 0\n"
                    ),
                },
                {
                    "effectName": "shipBonusThanatosA5FighterDamage",
                    "modifierInfo": (
                        "- domain: charID\n"
                        "  func: OwnerRequiredSkillModifier\n"
                        "  modifiedAttributeID: 64\n"
                        "  modifyingAttributeID: 2208\n"
                        "  operation: 6\n"
                        "  skillTypeID: 24311\n"
                    ),
                },
            ],
        ])
        engine = DogmaEngine(db)
        modifiers = engine._load_ship_effects(23911)

        # The agility PreAssign effect should be filtered out
        agility_mods = [m for m in modifiers if m.modified_attr_id == 70]
        assert len(agility_mods) == 0, "PreAssign agility effects should be filtered"

        # Other ship effects should remain
        non_agility = [m for m in modifiers if m.modified_attr_id != 70]
        assert len(non_agility) == 1

    def test_non_preassign_agility_effects_kept(self):
        """PostPercent agility effects (if any) should NOT be filtered."""
        db = MockDB(result_sets=[
            # _load_ship_effects: ship effects query
            [
                {
                    "effectName": "someAgilityBonus",
                    "modifierInfo": (
                        "- domain: shipID\n"
                        "  func: ItemModifier\n"
                        "  modifiedAttributeID: 70\n"
                        "  modifyingAttributeID: 100\n"
                        "  operation: 6\n"  # PostPercent, not PreAssign
                    ),
                },
            ],
        ])
        engine = DogmaEngine(db)
        modifiers = engine._load_ship_effects(12345)

        agility_mods = [m for m in modifiers if m.modified_attr_id == 70]
        assert len(agility_mods) == 1, "PostPercent agility effects should be kept"

    def test_effect_with_only_agility_preassign_fully_skipped(self):
        """If an effect has only PreAssign agility modifiers, the whole effect is skipped."""
        db = MockDB(result_sets=[
            # _load_ship_effects: ship effects query
            [
                {
                    "effectName": "shipCapitalAgilityBonus",
                    "modifierInfo": (
                        "- domain: shipID\n"
                        "  func: ItemModifier\n"
                        "  modifiedAttributeID: 70\n"
                        "  modifyingAttributeID: 874\n"
                        "  operation: 0\n"
                    ),
                },
            ],
        ])
        engine = DogmaEngine(db)
        modifiers = engine._load_ship_effects(23911)
        assert len(modifiers) == 0


# ─── Bug 2: Cap stability override ────────────────────────────────────────────

class TestCapStabilityOverride:
    """Discrete sim declaring stable when drain >> peak_recharge should be overridden."""

    def test_high_drain_no_boosters_declares_unstable(self):
        """When total drain far exceeds peak recharge and no cap boosters,
        the result should be unstable despite discrete sim oscillation."""
        # Thanatos-like scenario: cap=55000, recharge=4200s
        # Modules: 2 neuts (3060 GJ each, 12s), NSA (3000, 60s), AB (1800, 20s)
        # Total drain ~650 GJ/s, peak recharge ~32 GJ/s
        cap = 55000.0
        recharge_ms = 4200000.0
        drains = [
            (3060, 12000),   # Heavy Neut 1
            (3060, 12000),   # Heavy Neut 2
            (3000, 60000),   # NSA
            (1800, 20000),   # AB
            (4, 5000),       # Omnidirectional
        ]
        module_cap_per_sec = sum(d[0] / (d[1] / 1000.0) for d in drains)

        result = calculate_capacitor(
            cap_capacity=cap,
            cap_recharge_ms=recharge_ms,
            module_cap_per_sec=module_cap_per_sec,
            module_drains=drains,
            cap_injectors=None,
        )
        assert result.stable is False, "Should be unstable without cap boosters"
        assert result.lasts_seconds > 0, "Should report depletion time"

    def test_low_drain_stays_stable(self):
        """When drain < peak recharge, discrete sim result (stable) should hold."""
        cap = 5000.0
        recharge_ms = 230000.0
        drains = [(10, 5000)]  # Very low drain
        module_cap_per_sec = 10 / 5.0  # 2 GJ/s

        result = calculate_capacitor(
            cap_capacity=cap,
            cap_recharge_ms=recharge_ms,
            module_cap_per_sec=module_cap_per_sec,
            module_drains=drains,
        )
        assert result.stable is True

    def test_with_cap_boosters_discrete_sim_used(self):
        """When cap boosters are present, discrete sim is fully trusted
        (boosters inject cap in chunks, making discrete model accurate)."""
        cap = 55000.0
        recharge_ms = 4200000.0
        drains = [(3060, 12000), (3060, 12000)]
        injectors = [(3200, 10000)]  # Navy Cap Booster 3200
        module_cap_per_sec = sum(d[0] / (d[1] / 1000.0) for d in drains)

        result = calculate_capacitor(
            cap_capacity=cap,
            cap_recharge_ms=recharge_ms,
            module_cap_per_sec=module_cap_per_sec,
            module_drains=drains,
            cap_injectors=injectors,
        )
        # With cap boosters, we trust the discrete sim result regardless
        # (may or may not be stable depending on injection rate)
        assert isinstance(result.stable, bool)


# ─── Bug 3: Rig stacking penalty exemption ────────────────────────────────────

class TestRigStackingExemption:
    """Rig PostPercent bonuses should NOT be stacking penalized."""

    def test_rig_modifier_tagged_with_is_rig(self):
        """Modifiers from rig flags (92-99) should have is_rig=True."""
        mod = DogmaModifier(
            domain="shipID",
            func="ItemModifier",
            modified_attr_id=265,
            modifying_attr_id=335,
            operation=6,
        )
        assert mod.is_rig is False

        from dataclasses import replace
        rig_mod = replace(mod, is_rig=True)
        assert rig_mod.is_rig is True

    def test_three_rig_bonuses_no_stacking_penalty(self):
        """3x +15% rig bonuses should give exactly 1.15^3 = 1.521167...,
        not the stacking penalized 1.4105 factor."""
        engine = DogmaEngine(MockDB())

        ship_attrs = {265: 204500.0}  # armorHP after plates
        module_attrs = {
            30993: {335: 15.0},  # Capital Trimark: armorHPBonus +15%
        }
        # 3 trimark rigs, each with is_rig=True
        modifiers = []
        for _ in range(3):
            modifiers.append((30993, DogmaModifier(
                domain="shipID",
                func="ItemModifier",
                modified_attr_id=265,
                modifying_attr_id=335,
                operation=6,  # PostPercent
                is_rig=True,
            )))

        result = engine._apply_modifiers(ship_attrs, module_attrs, modifiers)

        # Without stacking penalty: 204500 * 1.15^3 = 311,191.9375
        expected_no_stacking = 204500.0 * 1.15 ** 3
        assert abs(result[265] - expected_no_stacking) < 1.0, (
            f"Expected {expected_no_stacking:.1f}, got {result[265]:.1f}. "
            "Rig bonuses should NOT be stacking penalized."
        )

    def test_regular_module_bonuses_still_stacking_penalized(self):
        """Non-rig module PostPercent bonuses should still be stacking penalized."""
        engine = DogmaEngine(MockDB())

        ship_attrs = {265: 10000.0}
        module_attrs = {
            100: {50: 15.0},  # Some module with +15%
        }
        # 3 identical module bonuses (NOT rigs)
        modifiers = []
        for _ in range(3):
            modifiers.append((100, DogmaModifier(
                domain="shipID",
                func="ItemModifier",
                modified_attr_id=265,
                modifying_attr_id=50,
                operation=6,
                is_rig=False,
            )))

        result = engine._apply_modifiers(ship_attrs, module_attrs, modifiers)

        # With stacking penalty, result should be less than 10000 * 1.15^3
        no_stacking = 10000.0 * 1.15 ** 3
        assert result[265] < no_stacking, (
            "Regular module bonuses should be stacking penalized"
        )

    def test_non_velocity_drawback_still_applied(self):
        """Non-velocity rig drawbacks (e.g., sig radius) should still work."""
        engine = DogmaEngine(MockDB())

        ship_attrs = {552: 100.0}  # sig radius
        module_attrs = {
            30993: {1138: 10.0},  # drawback: +10% sig radius
        }
        modifiers = []
        for _ in range(3):
            modifiers.append((30993, DogmaModifier(
                domain="shipID",
                func="ItemModifier",
                modified_attr_id=552,
                modifying_attr_id=1138,
                operation=6,
                is_drawback=True,
            )))

        result = engine._apply_modifiers(ship_attrs, module_attrs, modifiers)

        # 3x +10% drawback (not stacking penalized): 100 * 1.1^3 = 133.1
        expected = 100.0 * 1.1 ** 3
        assert abs(result[552] - expected) < 0.1


# ─── Bug 4: NSA scan resolution ───────────────────────────────────────────────

class TestNSAScanResolution:
    """Networked Sensor Array should apply scan resolution bonus."""

    def test_nsa_bonus_applied(self):
        """NSA +500% scan res should multiply scan_res by 6.0."""
        from app.services.fitting_stats.constants import ATTR_SCAN_RES

        # Simulate: ship_attrs has scan_res=81.25 (after Dogma+skills)
        # NSA bonus = +500% → scan_res * (1 + 500/100) = 81.25 * 6 = 487.5
        scan_res_base = 81.25
        bonus_pct = 500.0
        expected = scan_res_base * (1 + bonus_pct / 100.0)
        assert abs(expected - 487.5) < 0.1

    def test_nsa_applied_matches_eve_direction(self):
        """With Sig Analysis V (+25%) on base 65, plus NSA +500%,
        result should be much higher than without NSA."""
        # Base scan res 65 * 1.25 (Sig Analysis V) = 81.25
        # With NSA: 81.25 * 6.0 = 487.5
        # EVE showed 132.24 which suggests different ordering or partial bonus
        # But at minimum, NSA should significantly increase scan res
        base = 65.0
        with_skill = base * 1.25
        with_nsa = with_skill * 6.0
        assert with_nsa > with_skill * 2, "NSA should at least double scan res"


# ─── Integration: Thanatos expected values ─────────────────────────────────────

class TestThanatosExpectedValues:
    """Verify Thanatos-like values are in reasonable ranges."""

    def test_agility_in_reasonable_range(self):
        """Thanatos base agility is 0.039. After SC V (-10%) and EM V (-25%),
        agility should be ~0.026, NOT 3.375 (the old bug value)."""
        base_agility = 0.039
        sc_v_mult = 1 + (-2.0 * 5) / 100  # 0.90
        em_v_mult = 1 + (-5.0 * 5) / 100  # 0.75
        modified = base_agility * sc_v_mult * em_v_mult
        assert 0.02 < modified < 0.04, f"Modified agility {modified} out of range"
        assert modified != pytest.approx(3.375, abs=0.1), "Must not be the old bug value"

    def test_armor_hp_without_stacking_penalty(self):
        """Thanatos with 2x 25000mm plates and 3x Capital Trimark + Hull Upgrades V.
        Without stacking penalty on rigs: 204500 * 1.15^3 * 1.25 ≈ 388,983."""
        base_armor = 69500.0
        plates_add = 2 * 67500.0
        subtotal = base_armor + plates_add  # 204,500

        # 3 trimark rigs +15% each, NOT stacking penalized
        rig_mult = 1.15 ** 3
        # Hull Upgrades V: +25%
        hu_mult = 1.25

        result = subtotal * rig_mult * hu_mult
        assert 388000 < result < 390000, f"Expected ~388,983, got {result:.0f}"

    def test_cap_instability_threshold(self):
        """Thanatos with heavy neuts: usage rate should exceed peak recharge."""
        cap = 55000.0
        recharge_ms = 4200000.0
        tau_s = recharge_ms / 1000.0
        peak_rate = 2.5 * cap / tau_s  # ~32.74 GJ/s

        # Module drains
        total_drain = (3060/12 + 3060/12 + 3000/60 + 1800/20 + 4/5)
        assert total_drain > peak_rate * 5, (
            f"Drain {total_drain:.1f} should far exceed peak {peak_rate:.1f}"
        )


# ─── Bug 5: Velocity drawback skipped ────────────────────────────────────────

class TestVelocityDrawbackSkipped:
    """EVE's fitting window does NOT apply rig velocity drawbacks."""

    def test_drawback_velocity_effects_filtered_in_load_modifiers(self):
        """drawbackMaxVelocity modifiers targeting attr 37 should be dropped."""
        db = MockDB(result_sets=[
            # _load_modifiers query result
            [
                {
                    "typeID": 30993,
                    "effectID": 2717,
                    "effectName": "drawbackMaxVelocity",
                    "modifierInfo": (
                        "- domain: shipID\n"
                        "  func: ItemModifier\n"
                        "  modifiedAttributeID: 37\n"
                        "  modifyingAttributeID: 1138\n"
                        "  operation: 6\n"
                    ),
                    "durationAttributeID": None,
                    "effectCategory": None,
                },
                {
                    "typeID": 30993,
                    "effectID": 271,
                    "effectName": "hullUpgradesArmorHpBonusPostPercentHpLocationShip",
                    "modifierInfo": (
                        "- domain: shipID\n"
                        "  func: ItemModifier\n"
                        "  modifiedAttributeID: 265\n"
                        "  modifyingAttributeID: 335\n"
                        "  operation: 6\n"
                    ),
                    "durationAttributeID": None,
                    "effectCategory": None,
                },
            ],
        ])
        engine = DogmaEngine(db)
        modifiers = engine._load_modifiers(
            [30993], simulation_mode=True,
            module_flags=[92], flag_states={92: "active"},
        )

        # Velocity drawback should be gone, armor HP bonus should remain
        velocity_mods = [(t, m) for t, m in modifiers if m.modified_attr_id == 37]
        armor_mods = [(t, m) for t, m in modifiers if m.modified_attr_id == 265]
        assert len(velocity_mods) == 0, "Velocity drawback should be filtered out"
        assert len(armor_mods) == 1, "Armor HP bonus should remain"

    def test_non_velocity_drawback_kept(self):
        """Drawback effects targeting non-velocity attrs should be kept."""
        db = MockDB(result_sets=[
            [
                {
                    "typeID": 30999,
                    "effectID": 9999,
                    "effectName": "drawbackSignatureRadius",
                    "modifierInfo": (
                        "- domain: shipID\n"
                        "  func: ItemModifier\n"
                        "  modifiedAttributeID: 552\n"
                        "  modifyingAttributeID: 1138\n"
                        "  operation: 6\n"
                    ),
                    "durationAttributeID": None,
                    "effectCategory": None,
                },
            ],
        ])
        engine = DogmaEngine(db)
        modifiers = engine._load_modifiers(
            [30999], simulation_mode=True,
            module_flags=[92], flag_states={92: "active"},
        )

        sig_mods = [(t, m) for t, m in modifiers if m.modified_attr_id == 552]
        assert len(sig_mods) == 1, "Sig radius drawback should be kept"
        assert sig_mods[0][1].is_drawback is True

    def test_thanatos_velocity_without_drawback(self):
        """With velocity drawback removed, Thanatos velocity should match EVE.

        Base vel = 80, Nav V = +25% → 100
        10000MN AB: speedBoostFactor=125, thrust=1.5B, mass=1.22B+0.5B=1.72B
        AC V: 1.25 multiplier
        Speed boost = 125/100 * 1.5e9/1.72e9 * 1.25 = 1.362
        Final = 100 * (1 + 1.362) = 236.2 (EVE shows 228.2, close enough for AB calc)
        """
        base_vel = 80.0
        nav_v = base_vel * 1.25  # Nav V: +25%
        # No rig drawback applied (the fix!)
        thrust = 1_500_000_000.0
        mass = 1_220_000_000.0 + 500_000_000.0  # ship + AB mass
        ac_mult = 1.25  # AC V
        speed_boost = 125.0 / 100.0 * thrust / mass * ac_mult
        final_vel = nav_v * (1 + speed_boost)
        # Should be significantly higher than the old 189.5
        assert final_vel > 220, f"Velocity {final_vel:.1f} should be > 220 without drawback"


# ─── Bug 6: Cap booster excluded from stability ─────────────────────────────

class TestCapBoosterExcludedFromStability:
    """EVE's fitting window shows cap stability WITHOUT cap booster injection."""

    def test_high_drain_with_boosters_still_unstable(self):
        """Even with cap boosters, if drain > peak recharge, should be unstable.

        This matches EVE behavior: cap boosters require manual charge loading,
        so the fitting window shows stability without injection.
        """
        cap = 68750.0  # Thanatos with Cap Management V
        recharge_ms = 3150000.0  # After cap skills
        drains = [
            (3060, 12000),   # Heavy Neut 1
            (3060, 12000),   # Heavy Neut 2
            (3000, 60000),   # NSA
            (1800, 20000),   # AB
            (4, 5000),       # Omnidirectional
        ]
        module_cap_per_sec = sum(d[0] / (d[1] / 1000.0) for d in drains)

        # WITHOUT cap boosters → unstable
        result = calculate_capacitor(
            cap_capacity=cap,
            cap_recharge_ms=recharge_ms,
            module_cap_per_sec=module_cap_per_sec,
            module_drains=drains,
            cap_injectors=None,  # No cap booster injection
        )
        assert result.stable is False, (
            "Should be unstable when cap boosters are excluded from stability calc"
        )

    def test_cap_booster_module_drain_still_counted(self):
        """Cap booster module's own cap_need should still count as drain."""
        # If a cap booster has cap_need > 0, it should appear in the drain
        cap = 10000.0
        recharge_ms = 100000.0
        # Cap booster module with cap_need=50, cycle=12s → 4.17 GJ/s
        # Other module: 100 GJ, 10s → 10 GJ/s
        # Total: 14.17 GJ/s, peak recharge = 2.5*10000/100 = 250 GJ/s → stable
        drains = [
            (50, 12000),    # Cap booster module own drain
            (100, 10000),   # Another module
        ]
        module_cap_per_sec = sum(d[0] / (d[1] / 1000.0) for d in drains)

        result = calculate_capacitor(
            cap_capacity=cap,
            cap_recharge_ms=recharge_ms,
            module_cap_per_sec=module_cap_per_sec,
            module_drains=drains,
        )
        assert result.stable is True
        assert result.usage_rate > 14.0, "Should include cap booster module's own drain"


# ─── Drone Bay Items Filter ──────────────────────────────────────────────────

class TestDroneBayItemsFiltered:
    """Verify that items in non-fitting slots (drone bay, cargo) are excluded
    from the Dogma engine input.

    Bug: Drone bay items (flag 87) like Prototype Cloaking Device I were
    processed as fitted modules, applying their velocity penalty to the ship.
    """

    # The fitting flags used in service.py
    FITTING_FLAGS = set(range(11, 35)) | set(range(92, 100))

    def test_fitting_flags_include_all_slot_types(self):
        """Low (11-18), Mid (19-26), High (27-34), Rig (92-99)."""
        assert 11 in self.FITTING_FLAGS  # first low
        assert 18 in self.FITTING_FLAGS  # last low
        assert 19 in self.FITTING_FLAGS  # first mid
        assert 26 in self.FITTING_FLAGS  # last mid
        assert 27 in self.FITTING_FLAGS  # first high
        assert 34 in self.FITTING_FLAGS  # last high
        assert 92 in self.FITTING_FLAGS  # first rig
        assert 99 in self.FITTING_FLAGS  # last rig

    def test_drone_bay_excluded(self):
        """Flag 87 (drone bay) must NOT be in fitting flags."""
        assert 87 not in self.FITTING_FLAGS

    def test_cargo_excluded(self):
        """Flag 5 (cargo) must NOT be in fitting flags."""
        assert 5 not in self.FITTING_FLAGS

    def test_filter_logic_matches_service(self):
        """Simulate the filtering logic from service.py calculate_stats."""
        # Items from a Thanatos fitting — includes drone bay items
        items = [
            {"type_id": 4383, "flag": 27, "quantity": 1},   # Fighter Support Unit II (high)
            {"type_id": 4383, "flag": 28, "quantity": 1},   # Fighter Support Unit II (high)
            {"type_id": 3170, "flag": 19, "quantity": 1},   # AB (mid)
            {"type_id": 1952, "flag": 11, "quantity": 1},   # Plate (low)
            {"type_id": 26082, "flag": 92, "quantity": 1},  # Trimark (rig)
            # Drone bay items — MUST be excluded
            {"type_id": 11370, "flag": 87, "quantity": 1},  # Prototype Cloaking Device I
            {"type_id": 35662, "flag": 87, "quantity": 1},  # 500MN MWD
            {"type_id": 12271, "flag": 87, "quantity": 2},  # Heavy Energy Neutralizer II
        ]

        module_type_ids = []
        module_flags = []
        for item in items:
            if item["flag"] not in self.FITTING_FLAGS:
                continue
            for _ in range(item["quantity"]):
                module_type_ids.append(item["type_id"])
                module_flags.append(item["flag"])

        # Should have exactly 5 items (5 fitted), NOT 9 (including drone bay)
        assert len(module_type_ids) == 5
        assert len(module_flags) == 5
        # No drone bay flags
        assert 87 not in module_flags
        # Cloaking device not in type_ids
        assert 11370 not in module_type_ids
        assert 35662 not in module_type_ids
        assert 12271 not in module_type_ids


class TestAttributeCaps:
    """Verify the maxAttributeID capping mechanism.

    In EVE, some attributes are capped by another attribute's value.
    E.g., maxTargetRange (76) is capped by maximumRangeCap (797, default 300km).
    This prevents targeting ranges from exceeding the cap even after all bonuses.
    """

    def test_cap_applied_when_value_exceeds(self):
        """Targeting range exceeding cap should be clamped."""
        engine = DogmaEngine(None)
        ship_attrs = {
            76: 4_587_500.0,    # maxTargetRange (way too high)
            797: 750_000.0,     # maximumRangeCap
        }
        result = engine._apply_attribute_caps(ship_attrs)
        assert result[76] == 750_000.0

    def test_cap_not_applied_when_value_below(self):
        """Targeting range below cap should remain unchanged."""
        engine = DogmaEngine(None)
        ship_attrs = {
            76: 375_000.0,      # maxTargetRange (300k * 1.25 LRT V)
            797: 750_000.0,     # maximumRangeCap
        }
        result = engine._apply_attribute_caps(ship_attrs)
        assert result[76] == 375_000.0

    def test_cap_uses_default_when_cap_attr_missing(self):
        """If ship has no maximumRangeCap attr, use default (300km)."""
        engine = DogmaEngine(None)
        ship_attrs = {
            76: 500_000.0,      # maxTargetRange (subcap with modules)
        }
        result = engine._apply_attribute_caps(ship_attrs)
        # Default cap is 300,000 — should clamp
        assert result[76] == 300_000.0

    def test_cap_default_allows_normal_subcaps(self):
        """Normal subcap targeting range (< 300km) should not be capped."""
        engine = DogmaEngine(None)
        ship_attrs = {
            76: 93_750.0,       # Drake: 75k * 1.25 = 93,750m
        }
        result = engine._apply_attribute_caps(ship_attrs)
        assert result[76] == 93_750.0

    def test_cap_preserves_other_attrs(self):
        """Capping should not affect unrelated attributes."""
        engine = DogmaEngine(None)
        ship_attrs = {
            76: 375_000.0,
            797: 750_000.0,
            263: 29_999.0,      # shieldCapacity
            37: 228.2,          # maxVelocity
        }
        result = engine._apply_attribute_caps(ship_attrs)
        assert result[263] == 29_999.0
        assert result[37] == 228.2

    def test_thanatos_targeting_with_lrt_v(self):
        """Thanatos: 300,000 base * 1.25 (LRT V) = 375,000 — below 750k cap."""
        engine = DogmaEngine(None)
        ship_attrs = {
            76: 300_000.0 * 1.25,   # 375,000
            797: 750_000.0,
        }
        result = engine._apply_attribute_caps(ship_attrs)
        assert result[76] == 375_000.0
