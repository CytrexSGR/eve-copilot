import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { fittingApi } from '../services/api/fittings';
import { getShipRenderUrl } from '../types/fittings';
import type { CustomFitting, FittingStats } from '../types/fittings';

interface FittingSlot {
  fitting: CustomFitting | null;
  stats: FittingStats | null;
}

type StatRow = {
  label: string;
  key: string;
  extract: (s: FittingStats) => string;
  rawValue: (s: FittingStats) => number;
  higherIsBetter: boolean;
};

const STAT_ROWS: StatRow[] = [
  {
    label: 'DPS',
    key: 'dps',
    extract: (s) => s.offense.total_dps.toLocaleString(undefined, { maximumFractionDigits: 1 }),
    rawValue: (s) => s.offense.total_dps,
    higherIsBetter: true,
  },
  {
    label: 'EHP',
    key: 'ehp',
    extract: (s) => s.defense.total_ehp.toLocaleString(undefined, { maximumFractionDigits: 0 }),
    rawValue: (s) => s.defense.total_ehp,
    higherIsBetter: true,
  },
  {
    label: 'Speed',
    key: 'speed',
    extract: (s) => `${s.navigation.max_velocity.toLocaleString(undefined, { maximumFractionDigits: 1 })} m/s`,
    rawValue: (s) => s.navigation.max_velocity,
    higherIsBetter: true,
  },
  {
    label: 'Align Time',
    key: 'align',
    extract: (s) => `${s.navigation.align_time.toFixed(1)}s`,
    rawValue: (s) => s.navigation.align_time,
    higherIsBetter: false,
  },
  {
    label: 'Cap Stable',
    key: 'cap',
    extract: (s) => s.capacitor.stable ? `${s.capacitor.stable_percent.toFixed(1)}%` : `${s.capacitor.lasts_seconds.toFixed(0)}s`,
    rawValue: (s) => s.capacitor.stable ? s.capacitor.stable_percent + 1000 : s.capacitor.lasts_seconds,
    higherIsBetter: true,
  },
  {
    label: 'Shield Rep',
    key: 'shield_rep',
    extract: (s) => `${s.repairs.shield_rep.toFixed(1)} HP/s`,
    rawValue: (s) => s.repairs.shield_rep,
    higherIsBetter: true,
  },
  {
    label: 'Armor Rep',
    key: 'armor_rep',
    extract: (s) => `${s.repairs.armor_rep.toFixed(1)} HP/s`,
    rawValue: (s) => s.repairs.armor_rep,
    higherIsBetter: true,
  },
  {
    label: 'PG Used/Total',
    key: 'pg',
    extract: (s) => `${s.resources.pg_used.toFixed(0)} / ${s.resources.pg_total.toFixed(0)}`,
    rawValue: (s) => s.resources.pg_total > 0 ? (1 - s.resources.pg_used / s.resources.pg_total) : 0,
    higherIsBetter: true,
  },
  {
    label: 'CPU Used/Total',
    key: 'cpu',
    extract: (s) => `${s.resources.cpu_used.toFixed(0)} / ${s.resources.cpu_total.toFixed(0)}`,
    rawValue: (s) => s.resources.cpu_total > 0 ? (1 - s.resources.cpu_used / s.resources.cpu_total) : 0,
    higherIsBetter: true,
  },
];

const MAX_SLOTS = 4;

export function FittingComparison() {
  const { account } = useAuth();
  const [slots, setSlots] = useState<FittingSlot[]>([
    { fitting: null, stats: null },
    { fitting: null, stats: null },
  ]);
  const [availableFittings, setAvailableFittings] = useState<CustomFitting[]>([]);
  const [sharedFittings, setSharedFittings] = useState<CustomFitting[]>([]);
  const [loadingFittings, setLoadingFittings] = useState(true);
  const [loadingStats, setLoadingStats] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load available fittings on mount
  useEffect(() => {
    if (!account?.primary_character_id) return;
    setLoadingFittings(true);
    Promise.all([
      fittingApi.getCustomFittings(account.primary_character_id).catch(() => []),
      fittingApi.getSharedFittings({ limit: 100 }).catch(() => []),
    ]).then(([custom, shared]) => {
      setAvailableFittings(custom);
      // Deduplicate: remove shared fittings that are already in custom
      const customIds = new Set(custom.map(f => f.id));
      setSharedFittings(shared.filter(f => !customIds.has(f.id)));
      setLoadingFittings(false);
    });
  }, [account]);

  // Fetch stats when selections change
  const fetchStats = useCallback(async () => {
    const selectedSlots = slots.filter(s => s.fitting !== null);
    if (selectedSlots.length < 2) return;

    setLoadingStats(true);
    setError(null);

    try {
      const fittingPayloads = selectedSlots.map(s => ({
        ship_type_id: s.fitting!.ship_type_id,
        items: s.fitting!.items,
        charges: s.fitting!.charges,
      }));
      const result = await fittingApi.compareFittings(fittingPayloads);

      // Map stats back to slots
      let statIdx = 0;
      setSlots(prev => prev.map(s => {
        if (s.fitting !== null) {
          return { ...s, stats: result.comparisons[statIdx++] || null };
        }
        return { ...s, stats: null };
      }));
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to compare fittings';
      setError(message);
    } finally {
      setLoadingStats(false);
    }
  }, [slots]);

  useEffect(() => {
    const selectedCount = slots.filter(s => s.fitting !== null).length;
    if (selectedCount >= 2) {
      fetchStats();
    }
  // Only trigger when fitting selections change, not when stats update
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slots.map(s => s.fitting?.id).join(',')]);

  const handleSelectFitting = (slotIndex: number, fittingId: string) => {
    if (!fittingId) {
      setSlots(prev => {
        const next = [...prev];
        next[slotIndex] = { fitting: null, stats: null };
        return next;
      });
      return;
    }

    const id = parseInt(fittingId, 10);
    const allFittings = [...availableFittings, ...sharedFittings];
    const fitting = allFittings.find(f => f.id === id) || null;

    setSlots(prev => {
      const next = [...prev];
      next[slotIndex] = { fitting, stats: null };
      return next;
    });
  };

  const addSlot = () => {
    if (slots.length >= MAX_SLOTS) return;
    setSlots(prev => [...prev, { fitting: null, stats: null }]);
  };

  const removeSlot = (index: number) => {
    if (slots.length <= 2) return;
    setSlots(prev => prev.filter((_, i) => i !== index));
  };

  // Determine best/worst per row
  const getHighlights = (row: StatRow): { bestIdx: number; worstIdx: number } => {
    const values: { idx: number; val: number }[] = [];
    slots.forEach((s, i) => {
      if (s.stats) {
        values.push({ idx: i, val: row.rawValue(s.stats) });
      }
    });
    if (values.length < 2) return { bestIdx: -1, worstIdx: -1 };

    const sorted = [...values].sort((a, b) => a.val - b.val);
    const best = row.higherIsBetter ? sorted[sorted.length - 1] : sorted[0];
    const worst = row.higherIsBetter ? sorted[0] : sorted[sorted.length - 1];

    // Only highlight if values differ
    if (best.val === worst.val) return { bestIdx: -1, worstIdx: -1 };

    return { bestIdx: best.idx, worstIdx: worst.idx };
  };

  const selectedCount = slots.filter(s => s.fitting !== null).length;

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '1.5rem 1rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1.5rem' }}>
        <Link
          to="/fittings"
          style={{
            color: '#00d4ff',
            textDecoration: 'none',
            fontSize: '0.85rem',
          }}
        >
          &larr; Fittings
        </Link>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, margin: 0 }}>Fit Comparison</h1>
      </div>

      {/* Selectors Row */}
      <div style={{
        display: 'flex',
        gap: '0.75rem',
        flexWrap: 'wrap',
        marginBottom: '1.5rem',
        alignItems: 'flex-end',
      }}>
        {slots.map((slot, i) => (
          <div key={i} style={{ flex: '1 1 200px', minWidth: 180, maxWidth: 280 }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '0.25rem',
            }}>
              <label style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>
                Fit {i + 1}
              </label>
              {slots.length > 2 && (
                <button
                  onClick={() => removeSlot(i)}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: '#f85149',
                    cursor: 'pointer',
                    fontSize: '0.7rem',
                    padding: '0 2px',
                  }}
                >
                  Remove
                </button>
              )}
            </div>
            <select
              value={slot.fitting?.id?.toString() || ''}
              onChange={e => handleSelectFitting(i, e.target.value)}
              disabled={loadingFittings}
              style={{
                width: '100%',
                padding: '0.5rem',
                background: 'var(--bg-secondary)',
                border: '1px solid var(--border-color)',
                borderRadius: '4px',
                color: 'var(--text-primary)',
                fontSize: '0.8rem',
              }}
            >
              <option value="">-- Select Fitting --</option>
              {availableFittings.length > 0 && (
                <optgroup label="My Fittings">
                  {availableFittings.map(f => (
                    <option key={`c-${f.id}`} value={f.id.toString()}>
                      {f.ship_name} - {f.name}
                    </option>
                  ))}
                </optgroup>
              )}
              {sharedFittings.length > 0 && (
                <optgroup label="Shared Fittings">
                  {sharedFittings.map(f => (
                    <option key={`s-${f.id}`} value={f.id.toString()}>
                      {f.ship_name} - {f.name}
                    </option>
                  ))}
                </optgroup>
              )}
            </select>
          </div>
        ))}

        {slots.length < MAX_SLOTS && (
          <button
            onClick={addSlot}
            style={{
              padding: '0.5rem 1rem',
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-color)',
              borderRadius: '4px',
              color: '#00d4ff',
              cursor: 'pointer',
              fontSize: '0.8rem',
              alignSelf: 'flex-end',
            }}
          >
            + Add
          </button>
        )}
      </div>

      {/* Error */}
      {error && (
        <div style={{
          padding: '0.75rem',
          background: 'rgba(248, 81, 73, 0.1)',
          border: '1px solid rgba(248, 81, 73, 0.3)',
          borderRadius: '4px',
          color: '#f85149',
          fontSize: '0.8rem',
          marginBottom: '1rem',
        }}>
          {error}
        </div>
      )}

      {/* Info message when less than 2 selected */}
      {selectedCount < 2 && (
        <div style={{
          padding: '2rem',
          textAlign: 'center',
          color: 'var(--text-tertiary)',
          fontSize: '0.85rem',
        }}>
          Select at least 2 fittings to compare stats
        </div>
      )}

      {/* Loading */}
      {loadingStats && (
        <div style={{
          padding: '1rem',
          textAlign: 'center',
          color: 'var(--text-secondary)',
          fontSize: '0.85rem',
        }}>
          Calculating stats...
        </div>
      )}

      {/* Comparison Table */}
      {selectedCount >= 2 && !loadingStats && slots.some(s => s.stats) && (
        <div style={{ overflowX: 'auto' }}>
          <table style={{
            width: '100%',
            borderCollapse: 'collapse',
            fontSize: '0.8rem',
          }}>
            {/* Column Headers - Ship renders + names */}
            <thead>
              <tr>
                <th style={{
                  textAlign: 'left',
                  padding: '0.5rem',
                  borderBottom: '1px solid var(--border-color)',
                  color: 'var(--text-tertiary)',
                  fontWeight: 600,
                  minWidth: 120,
                }}>
                  Stat
                </th>
                {slots.map((slot, i) => (
                  <th key={i} style={{
                    padding: '0.5rem',
                    borderBottom: '1px solid var(--border-color)',
                    textAlign: 'center',
                    minWidth: 140,
                  }}>
                    {slot.fitting ? (
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.25rem' }}>
                        <img
                          src={getShipRenderUrl(slot.fitting.ship_type_id, 64)}
                          alt={slot.fitting.ship_name}
                          style={{ width: 48, height: 48, borderRadius: '4px' }}
                        />
                        <div style={{ color: 'var(--text-primary)', fontWeight: 600, fontSize: '0.75rem' }}>
                          {slot.fitting.ship_name}
                        </div>
                        <div style={{ color: '#00d4ff', fontSize: '0.7rem' }}>
                          {slot.fitting.name}
                        </div>
                      </div>
                    ) : (
                      <span style={{ color: 'var(--text-tertiary)' }}>--</span>
                    )}
                  </th>
                ))}
              </tr>
            </thead>

            {/* Stat Rows */}
            <tbody>
              {STAT_ROWS.map(row => {
                const highlights = getHighlights(row);
                return (
                  <tr key={row.key}>
                    <td style={{
                      padding: '0.5rem',
                      borderBottom: '1px solid var(--border-color)',
                      color: 'var(--text-secondary)',
                      fontWeight: 500,
                    }}>
                      {row.label}
                    </td>
                    {slots.map((slot, i) => {
                      const isBest = i === highlights.bestIdx;
                      const isWorst = i === highlights.worstIdx;
                      return (
                        <td key={i} style={{
                          padding: '0.5rem',
                          borderBottom: '1px solid var(--border-color)',
                          textAlign: 'center',
                          color: isBest ? '#3fb950' : isWorst ? '#f85149' : 'var(--text-primary)',
                          fontWeight: isBest ? 600 : 400,
                          fontFamily: 'monospace',
                        }}>
                          {slot.stats ? row.extract(slot.stats) : '--'}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default FittingComparison;
