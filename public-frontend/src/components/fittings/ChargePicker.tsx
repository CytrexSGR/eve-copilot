import { useState, useEffect } from 'react';
import { sdeApi } from '../../services/api/fittings';
import type { ChargeSummary } from '../../types/fittings';
import { getTypeIconUrl, DAMAGE_COLORS } from '../../types/fittings';

interface ChargePickerProps {
  weaponTypeId: number;
  onSelectCharge: (chargeTypeId: number) => void;
  onClose: () => void;
}

export function ChargePicker({ weaponTypeId, onSelectCharge, onClose }: ChargePickerProps) {
  const [charges, setCharges] = useState<ChargeSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    sdeApi.getCharges(weaponTypeId)
      .then(setCharges)
      .catch(() => setCharges([]))
      .finally(() => setLoading(false));
  }, [weaponTypeId]);

  // Group charges by group_name
  const grouped = charges.reduce<Record<string, ChargeSummary[]>>((acc, charge) => {
    const group = charge.group_name || 'Other';
    if (!acc[group]) acc[group] = [];
    acc[group].push(charge);
    return acc;
  }, {});

  const groupNames = Object.keys(grouped).sort();

  return (
    <div style={{
      background: 'var(--bg-secondary)',
      border: '1px solid rgba(0,212,255,0.3)',
      borderRadius: '8px',
      padding: '0.75rem',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '0.75rem',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <div style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: '#00d4ff',
          }} />
          <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>Select Ammo</span>
        </div>
        <button
          onClick={onClose}
          style={{
            padding: '2px 8px',
            background: 'transparent',
            border: '1px solid var(--border-color)',
            borderRadius: '4px',
            color: 'var(--text-secondary)',
            cursor: 'pointer',
            fontSize: '0.75rem',
          }}
        >
          Close
        </button>
      </div>

      <div style={{ maxHeight: '500px', overflowY: 'auto' }}>
        {loading && (
          <div style={{ padding: '1rem', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Loading charges...
          </div>
        )}

        {!loading && charges.length === 0 && (
          <div style={{ padding: '1rem', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            No compatible charges found
          </div>
        )}

        {!loading && groupNames.map(groupName => (
          <div key={groupName} style={{ marginBottom: '0.75rem' }}>
            <div style={{
              fontSize: '0.7rem',
              fontWeight: 600,
              color: 'var(--text-tertiary)',
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
              marginBottom: '0.25rem',
              padding: '0 0.25rem',
            }}>
              {groupName}
            </div>

            {grouped[groupName].map(charge => {
              const totalDmg = (charge.em ?? 0) + (charge.thermal ?? 0) + (charge.kinetic ?? 0) + (charge.explosive ?? 0);

              return (
                <div
                  key={charge.type_id}
                  onClick={() => onSelectCharge(charge.type_id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    padding: '0.4rem',
                    cursor: 'pointer',
                    borderRadius: '4px',
                    marginBottom: '2px',
                  }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-elevated)')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                >
                  <img
                    src={getTypeIconUrl(charge.type_id, 32)}
                    alt={charge.name}
                    style={{ width: 28, height: 28, borderRadius: 4 }}
                  />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: '0.8rem', fontWeight: 500 }}>{charge.name}</div>
                    {/* Damage breakdown bar */}
                    {totalDmg > 0 && (
                      <div style={{
                        display: 'flex',
                        height: 4,
                        borderRadius: 2,
                        overflow: 'hidden',
                        marginTop: '3px',
                        background: 'rgba(255,255,255,0.05)',
                      }}>
                        {(charge.em ?? 0) > 0 && (
                          <div style={{
                            width: `${((charge.em ?? 0) / totalDmg) * 100}%`,
                            background: DAMAGE_COLORS.em,
                          }} />
                        )}
                        {(charge.thermal ?? 0) > 0 && (
                          <div style={{
                            width: `${((charge.thermal ?? 0) / totalDmg) * 100}%`,
                            background: DAMAGE_COLORS.thermal,
                          }} />
                        )}
                        {(charge.kinetic ?? 0) > 0 && (
                          <div style={{
                            width: `${((charge.kinetic ?? 0) / totalDmg) * 100}%`,
                            background: DAMAGE_COLORS.kinetic,
                          }} />
                        )}
                        {(charge.explosive ?? 0) > 0 && (
                          <div style={{
                            width: `${((charge.explosive ?? 0) / totalDmg) * 100}%`,
                            background: DAMAGE_COLORS.explosive,
                          }} />
                        )}
                      </div>
                    )}
                  </div>
                  {/* Damage numbers */}
                  {totalDmg > 0 && (
                    <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', fontFamily: 'monospace', whiteSpace: 'nowrap' }}>
                      {(charge.em ?? 0) > 0 ? (charge.em ?? 0).toFixed(0) : '-'}/
                      {(charge.thermal ?? 0) > 0 ? (charge.thermal ?? 0).toFixed(0) : '-'}/
                      {(charge.kinetic ?? 0) > 0 ? (charge.kinetic ?? 0).toFixed(0) : '-'}/
                      {(charge.explosive ?? 0) > 0 ? (charge.explosive ?? 0).toFixed(0) : '-'}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ))}

        {/* Damage type legend */}
        {!loading && charges.length > 0 && (
          <div style={{
            display: 'flex',
            gap: '0.75rem',
            padding: '0.5rem 0.25rem',
            borderTop: '1px solid var(--border-color)',
            marginTop: '0.5rem',
          }}>
            {(['em', 'thermal', 'kinetic', 'explosive'] as const).map(type => (
              <div key={type} style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
                <div style={{ width: 6, height: 6, borderRadius: '50%', background: DAMAGE_COLORS[type] }} />
                <span style={{ fontSize: '0.6rem', color: 'var(--text-tertiary)', textTransform: 'capitalize' }}>
                  {type.slice(0, 2).toUpperCase()}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
