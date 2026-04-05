"""Pure calculation functions — no DB or service dependencies."""

import math
from typing import List, Tuple

from .models import CapacitorStats


def calculate_capacitor(cap_capacity: float, cap_recharge_ms: float,
                        module_cap_per_sec: float,
                        module_drains: List[Tuple[float, float]] = None,
                        cap_injectors: List[Tuple[float, float]] = None) -> CapacitorStats:
    """EVE capacitor simulation.

    Peak recharge at 25% cap.
    Recharge at fraction x: rate(x) = 10 * cap / tau_s * (sqrt(x) - x)
    Peak rate = 2.5 * cap / tau_s

    Uses EVE-style discrete simulation when module_drains are provided:
    modules cannot activate when cap is insufficient (they wait/skip).
    This allows cap to stabilize at very low % even when average drain
    exceeds peak recharge — matching EVE client behavior.

    Args:
        module_drains: [(cap_need_gj, cycle_time_ms), ...] for discrete sim.
                       If provided, uses EVE-style discrete activation model.
        cap_injectors: [(inject_gj, cycle_time_ms), ...] for cap booster modules.
    """
    if cap_capacity <= 0 or cap_recharge_ms <= 0:
        return CapacitorStats()

    tau_s = cap_recharge_ms / 1000.0
    peak_rate = 2.5 * cap_capacity / tau_s

    if module_cap_per_sec <= 0:
        return CapacitorStats(
            capacity=round(cap_capacity, 1),
            recharge_time=round(tau_s, 1),
            peak_recharge_rate=round(peak_rate, 2),
            usage_rate=0,
            stable=True,
            stable_percent=100.0,
        )

    # Use discrete simulation when module drain list is available.
    # This correctly handles EVE's "can't activate if no cap" mechanic
    # which can stabilize cap at very low % even when avg drain > peak.
    if module_drains:
        result = _simulate_discrete_stability(
            cap_capacity, tau_s, module_drains, cap_injectors)

        # Sanity check: EVE's fitting window treats the fit as unstable when
        # total drain exceeds peak recharge — even if the discrete sim shows
        # "stable" because high-cap modules skip activation.  Without cap
        # boosters there is no external injection to compensate, so the ship
        # cannot actually sustain all active modules.
        if result["stable"] and module_cap_per_sec >= peak_rate and not cap_injectors:
            elapsed = _simulate_continuous(cap_capacity, tau_s, module_cap_per_sec)
            return CapacitorStats(
                capacity=round(cap_capacity, 1),
                recharge_time=round(tau_s, 1),
                peak_recharge_rate=round(peak_rate, 2),
                usage_rate=round(module_cap_per_sec, 2),
                stable=False,
                stable_percent=0,
                lasts_seconds=round(elapsed, 1),
            )

        return CapacitorStats(
            capacity=round(cap_capacity, 1),
            recharge_time=round(tau_s, 1),
            peak_recharge_rate=round(peak_rate, 2),
            usage_rate=round(module_cap_per_sec, 2),
            stable=result["stable"],
            stable_percent=result["stable_percent"],
            lasts_seconds=result.get("lasts_seconds", 0),
        )

    # Analytical fallback (no module drain list — continuous model)
    if module_cap_per_sec >= peak_rate:
        elapsed = _simulate_continuous(cap_capacity, tau_s, module_cap_per_sec)
        return CapacitorStats(
            capacity=round(cap_capacity, 1),
            recharge_time=round(tau_s, 1),
            peak_recharge_rate=round(peak_rate, 2),
            usage_rate=round(module_cap_per_sec, 2),
            stable=False,
            stable_percent=0,
            lasts_seconds=round(elapsed, 1),
        )

    # Stable (continuous) — find equilibrium on the right side of peak
    def recharge_at(x: float) -> float:
        if x <= 0:
            return 0
        return 10.0 * cap_capacity / tau_s * (math.sqrt(x) - x)

    lo, hi = 0.25, 1.0
    for _ in range(50):
        mid = (lo + hi) / 2
        if recharge_at(mid) > module_cap_per_sec:
            lo = mid
        else:
            hi = mid

    stable_pct = round(lo * 100, 1)
    return CapacitorStats(
        capacity=round(cap_capacity, 1),
        recharge_time=round(tau_s, 1),
        peak_recharge_rate=round(peak_rate, 2),
        usage_rate=round(module_cap_per_sec, 2),
        stable=True,
        stable_percent=stable_pct,
    )


def _simulate_discrete_stability(
    cap_capacity: float, tau_s: float,
    module_drains: List[Tuple[float, float]],
    cap_injectors: List[Tuple[float, float]] = None,
) -> dict:
    """EVE-style discrete cap simulation with stability detection.

    Key EVE behavior: if a module can't afford to activate (cap < cap_need),
    it WAITS — the activation is delayed until cap recharges enough.
    This means cap never goes below 0, and high-drain modules effectively
    reduce their firing rate at low cap, allowing stabilization.

    Returns dict with:
        stable: bool
        stable_percent: float (0-100)
        lasts_seconds: float (only if unstable)
    """
    # Build module state: [cap_need, cycle_time_s, next_activation_time]
    modules = []
    for cap_need, cycle_ms in (module_drains or []):
        if cap_need <= 0 or cycle_ms <= 0:
            continue
        modules.append([cap_need, cycle_ms / 1000.0, 0.0])

    # Build injector state: [inject_gj, cycle_time_s, next_activation_time]
    injectors = []
    for inject_gj, cycle_ms in (cap_injectors or []):
        if inject_gj <= 0 or cycle_ms <= 0:
            continue
        injectors.append([inject_gj, cycle_ms / 1000.0, 0.0])

    if not modules and not injectors:
        return {"stable": True, "stable_percent": 100.0}

    cap = cap_capacity
    max_sim = 6000.0  # 100 minutes — enough to detect stability
    stability_window = 300.0  # last 5 minutes for stability check
    window_start = max_sim - stability_window
    cap_sum_in_window = 0.0
    window_samples = 0

    # Initial activation at t=0: modules fire if cap allows
    for mod in modules:
        if cap >= mod[0]:
            cap -= mod[0]
            mod[2] = mod[1]  # next activation after one cycle
        else:
            mod[2] = 0.0  # will retry next tick

    for inj in injectors:
        cap = min(cap + inj[0], cap_capacity)
        inj[2] = inj[1]

    # Track if cap stays at ~0 for an extended time — true depletion
    stalled_ticks = 0
    elapsed = 0.0

    while elapsed < max_sim:
        elapsed += 1.0

        # EVE tick order: 1) Module activations, 2) Passive recharge
        # This matches EVE server behavior where drains happen first,
        # then passive recharge restores some cap before the next tick.

        # 1. Check module activations — only fire if cap allows
        for mod in modules:
            if elapsed >= mod[2] and cap >= mod[0]:
                cap -= mod[0]
                mod[2] = elapsed + mod[1]
            # If can't afford: mod[2] stays in the past, will retry next tick

        # 2. Check injector activations
        for inj in injectors:
            if elapsed >= inj[2]:
                cap = min(cap + inj[0], cap_capacity)
                inj[2] = elapsed + inj[1]

        # 3. Apply passive recharge for this tick
        x = max(cap / cap_capacity, 0.0)
        recharge = 10.0 * cap_capacity / tau_s * (math.sqrt(x) - x)
        cap = min(cap + recharge, cap_capacity)

        # Clamp cap to 0
        cap = max(cap, 0.0)

        # Track stability window — average cap over last N seconds
        if elapsed >= window_start:
            cap_sum_in_window += cap
            window_samples += 1

        # Detect true depletion: cap stuck at ~0 with no recovery
        if cap <= 0.01:
            stalled_ticks += 1
            if stalled_ticks > 120:
                # Cap stuck at ~0 for 120s — truly depleted
                return {
                    "stable": False,
                    "stable_percent": 0,
                    "lasts_seconds": round(elapsed - 120, 1),
                }
        else:
            stalled_ticks = 0

    # Sim completed without depletion — stable
    # Report the average cap % during the stability window (matches EVE display)
    if window_samples > 0:
        avg_cap = cap_sum_in_window / window_samples
        stable_pct = round((avg_cap / cap_capacity) * 100, 1)
    else:
        stable_pct = 100.0
    return {"stable": True, "stable_percent": max(stable_pct, 0.1)}


def _simulate_continuous(cap_capacity: float, tau_s: float,
                         drain_per_sec: float) -> float:
    """Continuous drain simulation (fallback when no module list available)."""
    dt = 1.0
    cap = cap_capacity
    elapsed = 0.0
    max_sim = 86400.0
    while cap > 0 and elapsed < max_sim:
        x = cap / cap_capacity
        recharge = 10.0 * cap_capacity / tau_s * (math.sqrt(x) - x)
        cap += (recharge - drain_per_sec) * dt
        elapsed += dt
        if cap <= 0:
            break
    return round(elapsed, 1)


def calculate_align_time(mass: float, agility: float) -> float:
    """EVE align time = -ln(0.25) * mass * agility / 1,000,000.

    Returns the continuous value (as displayed in EVE client simulation).
    Actual server applies tick quantization (ceil to next second),
    but the fitting window shows the continuous value.
    Ref: userdocs/dogma/formulas-navigation.md Section 1.1
    """
    if mass <= 0 or agility <= 0:
        return 0.0
    raw = -math.log(0.25) * mass * agility / 1_000_000
    return round(raw, 2)


def calculate_lock_time(scan_resolution: float, sig_radius: float) -> float:
    """EVE target lock time = 40000 / (scan_resolution * asinh(sig_radius)^2).

    Returns seconds. Minimum 1s (server tick).
    Ref: userdocs/dogma/formulas-navigation.md Section 3
    """
    if scan_resolution <= 0 or sig_radius <= 0:
        return 0
    raw = 40000.0 / (scan_resolution * math.asinh(sig_radius) ** 2)
    return round(max(raw, 1.0), 2)


def calculate_shield_peak_regen(shield_hp: float, recharge_time_ms: float) -> float:
    """Peak shield regen at 25% shield. Formula: 2.5 * shieldHP / tau_s.

    Ref: userdocs/dogma/formulas-defense.md Section 1.2
    """
    if shield_hp <= 0 or recharge_time_ms <= 0:
        return 0
    tau_s = recharge_time_ms / 1000.0
    return round(2.5 * shield_hp / tau_s, 2)


def calculate_rep_rate(repair_amount: float, cycle_time_ms: float) -> float:
    """Active repair HP/s = amount / (cycle_time / 1000).

    Ref: userdocs/dogma/formulas-defense.md Section 3
    """
    if repair_amount <= 0 or cycle_time_ms <= 0:
        return 0
    return round(repair_amount / (cycle_time_ms / 1000.0), 2)


def calculate_weapon_dps(damage_mult: float, rate_of_fire_ms: float,
                         charge_em: float, charge_thermal: float,
                         charge_kinetic: float, charge_explosive: float) -> dict:
    """Calculate DPS for a single weapon with given charge.

    Returns dict with keys: dps, em, thermal, kinetic, explosive, volley
    """
    if rate_of_fire_ms <= 0 or damage_mult <= 0:
        return {"dps": 0, "em": 0, "thermal": 0, "kinetic": 0, "explosive": 0, "volley": 0}

    total_charge_dmg = charge_em + charge_thermal + charge_kinetic + charge_explosive
    volley = damage_mult * total_charge_dmg
    dps = volley / (rate_of_fire_ms / 1000.0)

    # DPS breakdown proportional to charge damage types
    if total_charge_dmg > 0:
        em_dps = dps * charge_em / total_charge_dmg
        th_dps = dps * charge_thermal / total_charge_dmg
        ki_dps = dps * charge_kinetic / total_charge_dmg
        ex_dps = dps * charge_explosive / total_charge_dmg
    else:
        em_dps = th_dps = ki_dps = ex_dps = 0

    return {"dps": dps, "em": em_dps, "thermal": th_dps, "kinetic": ki_dps, "explosive": ex_dps, "volley": volley}


def calculate_drone_dps(drone_damage_mult: float, drone_rof_ms: float,
                        em: float, thermal: float, kinetic: float, explosive: float,
                        count: int = 1) -> dict:
    """Calculate DPS for drone(s).

    Drones have their own damage attributes and damage multiplier.
    Returns dict with keys: dps, em, thermal, kinetic, explosive
    """
    if drone_rof_ms <= 0 or drone_damage_mult <= 0 or count <= 0:
        return {"dps": 0, "em": 0, "thermal": 0, "kinetic": 0, "explosive": 0}

    total_dmg = em + thermal + kinetic + explosive
    volley = drone_damage_mult * total_dmg
    dps_per_drone = volley / (drone_rof_ms / 1000.0)
    total_dps = dps_per_drone * count

    if total_dmg > 0:
        em_dps = total_dps * em / total_dmg
        th_dps = total_dps * thermal / total_dmg
        ki_dps = total_dps * kinetic / total_dmg
        ex_dps = total_dps * explosive / total_dmg
    else:
        em_dps = th_dps = ki_dps = ex_dps = 0

    return {"dps": total_dps, "em": em_dps, "thermal": th_dps, "kinetic": ki_dps, "explosive": ex_dps}


def calculate_turret_hit_chance(
    angular_velocity: float, tracking: float, weapon_sig_res: float,
    target_sig: float, distance: float, optimal: float, falloff: float,
) -> float:
    """EVE turret hit chance formula.

    P = 0.5 ^ ((angular * sigRes / (tracking * sigTarget))^2
                + (max(0, distance - optimal) / falloff)^2)

    Ref: userdocs/dogma/formulas-combat.md Section 2
    """
    if tracking <= 0 or target_sig <= 0 or falloff <= 0:
        return 1.0 if angular_velocity == 0 else 0.0

    tracking_term = 0
    if angular_velocity > 0:
        tracking_term = (angular_velocity * weapon_sig_res / (tracking * target_sig)) ** 2

    range_term = 0
    if distance > optimal and falloff > 0:
        range_term = ((distance - optimal) / falloff) ** 2

    exponent = tracking_term + range_term
    if exponent <= 0:
        return 1.0
    return min(1.0, 0.5 ** exponent)


def calculate_missile_application(
    target_sig: float, target_velocity: float,
    explosion_radius: float, explosion_velocity: float, drf: float,
) -> float:
    """EVE missile damage application formula.

    damage_factor = min(1, sigT/expR, (sigT/expR * expV/targetV) ^ DRF)

    Ref: userdocs/dogma/formulas-combat.md Section 3
    """
    if explosion_radius <= 0:
        return 1.0

    sig_ratio = target_sig / explosion_radius

    if target_velocity <= 0:
        # Stationary target: only sig matters
        return min(1.0, sig_ratio)

    if explosion_velocity <= 0:
        return min(1.0, sig_ratio)

    vel_ratio = explosion_velocity / target_velocity
    velocity_term = (sig_ratio * vel_ratio) ** drf

    return min(1.0, sig_ratio, velocity_term)


def calculate_warp_time(warp_speed_au: float, distance_au: float) -> float:
    """EVE warp time: 3 phases (accel, cruise, decel).

    Accel: exactly 1 AU, v(t) = e^(k_accel * t), k_accel = warp_speed_au
    Decel: k_decel = min(warp_speed_au / 3, 2.0) — capped at 6 AU/s
    Cruise: remaining distance at max warp speed

    Ref: userdocs/dogma/formulas-navigation.md Section 2
    """
    if warp_speed_au <= 0 or distance_au <= 0:
        return 0

    AU_IN_M = 149_597_870_700.0
    max_speed_mps = warp_speed_au * AU_IN_M

    k_accel = warp_speed_au
    k_decel = min(warp_speed_au / 3.0, 2.0)

    # Acceleration: covers exactly 1 AU
    t_accel = math.log(max_speed_mps) / k_accel if k_accel > 0 else 0
    accel_dist_au = 1.0

    # Deceleration: mirrors accel with k_decel coefficient
    t_decel = math.log(max_speed_mps) / k_decel if k_decel > 0 else 0
    decel_dist_au = k_accel / k_decel if k_decel > 0 else 0

    if distance_au <= accel_dist_au + decel_dist_au:
        # Short warp: no cruise phase, simplified proportional scaling
        fraction = distance_au / (accel_dist_au + decel_dist_au)
        return round((t_accel + t_decel) * fraction, 1)

    # Cruise phase: remaining distance at max warp speed
    cruise_dist_au = distance_au - accel_dist_au - decel_dist_au
    t_cruise = cruise_dist_au / warp_speed_au  # AU / (AU/s) = seconds

    return round(t_accel + t_cruise + t_decel, 1)


def calculate_effective_rep(raw_hp_per_sec: float, avg_damage_pass_through: float) -> float:
    """Convert raw HP/s to EHP/s using average damage pass-through.

    avg_damage_pass_through = weighted average of (1-resist) across 4 damage types.
    Ref: userdocs/dogma/formulas-defense.md Section 3.4
    """
    if raw_hp_per_sec <= 0 or avg_damage_pass_through <= 0:
        return 0
    return round(raw_hp_per_sec / avg_damage_pass_through, 1)


def calculate_scanability(sig_radius: float, sensor_strength: float) -> float:
    """Scanability ratio = sig_radius / sensor_strength.

    Higher = easier to probe scan. Lower = harder to find.
    Ref: userdocs/dogma/formulas-scanning.md Section 1
    """
    if sensor_strength <= 0:
        return 0
    return round(sig_radius / sensor_strength, 2)


def calculate_sustainable_tank(
    raw_shield_rep: float, raw_armor_rep: float,
    cap_stable: bool, cap_stable_pct: float,
    rep_cap_need_per_sec: float,
    cap_recharge_rate: float,
) -> dict:
    """Calculate sustainable rep rates considering cap limitations.

    When cap is stable, full rep rate is sustainable.
    When cap is unstable, rep rate is limited by the ratio of cap
    recharge rate to total rep cap consumption.

    Returns: {"shield_sustained": hp/s, "armor_sustained": hp/s}
    """
    if rep_cap_need_per_sec <= 0:
        return {"shield_sustained": raw_shield_rep, "armor_sustained": raw_armor_rep}

    if cap_stable:
        # Cap stable — full rep rate sustained
        return {"shield_sustained": raw_shield_rep, "armor_sustained": raw_armor_rep}

    # Cap unstable — rep limited by cap availability
    cap_ratio = min(1.0, cap_recharge_rate / rep_cap_need_per_sec) if rep_cap_need_per_sec > 0 else 1.0
    return {
        "shield_sustained": round(raw_shield_rep * cap_ratio, 1),
        "armor_sustained": round(raw_armor_rep * cap_ratio, 1),
    }
