import { useState, useEffect } from 'react';
import { doctrineStatsApi } from '../../services/api/srp';
import type { FleetReadiness, FleetReadinessPilot } from '../../types/srp';

interface Props {
  doctrineId: number;
  corpId: number;
}

const STATUS_CONFIG: Record<FleetReadinessPilot['status'], { label: string; color: string }> = {
  can_fly:    { label: 'Can Fly',    color: '#56d364' },
  partial:    { label: 'Partial',    color: '#f0883e' },
  cannot_fly: { label: 'Cannot Fly', color: '#f85149' },
  unknown:    { label: 'Unknown',    color: '#8b949e' },
};

const CARD_DEFS = [
  { key: 'total_pilots'  as const, label: 'Total Pilots', color: '#58a6ff' },
  { key: 'can_fly'       as const, label: 'Can Fly',      color: '#56d364' },
  { key: 'partial'       as const, label: 'Partial',      color: '#f0883e' },
  { key: 'cannot_fly'    as const, label: 'Cannot Fly',   color: '#f85149' },
];

export function FleetReadinessPanel({ doctrineId, corpId }: Props) {
  const [data, setData] = useState<FleetReadiness | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    doctrineStatsApi.getFleetReadiness(doctrineId, corpId)
      .then(res => { if (!cancelled) setData(res); })
      .catch(err => { if (!cancelled) setError(err?.message || 'Failed to load fleet readiness'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [doctrineId, corpId]);

  if (loading) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '0.85rem' }}>
        Loading fleet readiness...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: '1.5rem', textAlign: 'center', color: '#f85149', fontSize: '0.85rem' }}>
        {error}
      </div>
    );
  }

  if (!data) return null;

  const total = data.total_pilots || 1;
  const canFlyPct = (data.can_fly / total) * 100;
  const partialPct = (data.partial / total) * 100;
  const cannotFlyPct = (data.cannot_fly / total) * 100;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {/* Summary cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.75rem' }}>
        {CARD_DEFS.map(card => (
          <div
            key={card.key}
            style={{
              background: `${card.color}10`,
              border: `1px solid ${card.color}30`,
              borderRadius: '8px',
              padding: '0.75rem 1rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.25rem',
            }}
          >
            <span style={{ fontSize: '0.65rem', fontWeight: 700, textTransform: 'uppercase', color: `${card.color}99` }}>
              {card.label}
            </span>
            <span style={{ fontSize: '1.5rem', fontWeight: 700, color: card.color, fontFamily: 'monospace' }}>
              {data[card.key]}
            </span>
          </div>
        ))}
      </div>

      {/* Readiness bar */}
      <div style={{
        background: 'rgba(0,0,0,0.2)',
        border: '1px solid var(--border-color)',
        borderRadius: '6px',
        padding: '0.75rem 1rem',
      }}>
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          marginBottom: '0.5rem',
        }}>
          <span style={{ fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase', color: 'rgba(255,255,255,0.45)' }}>
            Fleet Readiness
          </span>
          <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#58a6ff', fontFamily: 'monospace' }}>
            {data.readiness_pct.toFixed(1)}%
          </span>
        </div>
        <div style={{
          display: 'flex', height: '20px', borderRadius: '4px', overflow: 'hidden',
          background: 'rgba(255,255,255,0.05)',
        }}>
          {canFlyPct > 0 && (
            <div
              style={{
                width: `${canFlyPct}%`, background: '#56d364',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: '0.65rem', fontWeight: 700, color: '#000',
                minWidth: canFlyPct > 8 ? undefined : '0',
              }}
              title={`Can Fly: ${canFlyPct.toFixed(1)}%`}
            >
              {canFlyPct > 8 ? `${canFlyPct.toFixed(0)}%` : ''}
            </div>
          )}
          {partialPct > 0 && (
            <div
              style={{
                width: `${partialPct}%`, background: '#f0883e',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: '0.65rem', fontWeight: 700, color: '#000',
                minWidth: partialPct > 8 ? undefined : '0',
              }}
              title={`Partial: ${partialPct.toFixed(1)}%`}
            >
              {partialPct > 8 ? `${partialPct.toFixed(0)}%` : ''}
            </div>
          )}
          {cannotFlyPct > 0 && (
            <div
              style={{
                width: `${cannotFlyPct}%`, background: '#f85149',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: '0.65rem', fontWeight: 700, color: '#000',
                minWidth: cannotFlyPct > 8 ? undefined : '0',
              }}
              title={`Cannot Fly: ${cannotFlyPct.toFixed(1)}%`}
            >
              {cannotFlyPct > 8 ? `${cannotFlyPct.toFixed(0)}%` : ''}
            </div>
          )}
        </div>
      </div>

      {/* Pilot table */}
      <div style={{
        background: 'rgba(0,0,0,0.2)',
        border: '1px solid var(--border-color)',
        borderRadius: '6px',
        overflow: 'hidden',
      }}>
        {/* Header */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1.5fr 110px 80px 80px 100px',
          gap: '0.5rem',
          padding: '0.5rem 1rem',
          borderBottom: '1px solid var(--border-color)',
          fontSize: '0.65rem',
          fontWeight: 700,
          textTransform: 'uppercase',
          color: 'rgba(255,255,255,0.45)',
        }}>
          <span>Pilot</span>
          <span>Status</span>
          <span style={{ textAlign: 'right' }}>DPS %</span>
          <span style={{ textAlign: 'right' }}>EHP %</span>
          <span style={{ textAlign: 'right' }}>Missing Skills</span>
        </div>

        {/* Rows */}
        <div style={{ maxHeight: '360px', overflowY: 'auto' }}>
          {data.pilots.length === 0 ? (
            <div style={{ padding: '1.5rem', textAlign: 'center', color: 'rgba(255,255,255,0.3)', fontSize: '0.8rem' }}>
              No pilot data available
            </div>
          ) : (
            data.pilots.map((pilot, idx) => {
              const cfg = STATUS_CONFIG[pilot.status] || STATUS_CONFIG.unknown;
              return (
                <div
                  key={pilot.character_id}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1.5fr 110px 80px 80px 100px',
                    gap: '0.5rem',
                    padding: '0.4rem 1rem',
                    fontSize: '0.8rem',
                    background: idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)',
                    borderBottom: '1px solid rgba(255,255,255,0.03)',
                    alignItems: 'center',
                  }}
                >
                  {/* Pilot name + portrait */}
                  <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <img
                      src={`https://images.evetech.net/characters/${pilot.character_id}/portrait?size=32`}
                      alt=""
                      style={{ width: 24, height: 24, borderRadius: '3px', flexShrink: 0 }}
                      loading="lazy"
                    />
                    <span style={{ color: 'rgba(255,255,255,0.85)', fontWeight: 500 }}>
                      {pilot.character_name}
                    </span>
                  </span>

                  {/* Status badge */}
                  <span>
                    <span style={{
                      display: 'inline-block',
                      padding: '2px 8px',
                      borderRadius: '3px',
                      fontSize: '0.7rem',
                      fontWeight: 600,
                      background: `${cfg.color}20`,
                      color: cfg.color,
                      border: `1px solid ${cfg.color}40`,
                    }}>
                      {cfg.label}
                    </span>
                  </span>

                  {/* DPS % */}
                  <span style={{
                    textAlign: 'right',
                    fontFamily: 'monospace',
                    fontSize: '0.78rem',
                    color: pilot.dps_ratio >= 0.9 ? '#56d364' : pilot.dps_ratio >= 0.5 ? '#f0883e' : '#f85149',
                  }}>
                    {(pilot.dps_ratio * 100).toFixed(0)}%
                  </span>

                  {/* EHP % */}
                  <span style={{
                    textAlign: 'right',
                    fontFamily: 'monospace',
                    fontSize: '0.78rem',
                    color: pilot.ehp_ratio >= 0.9 ? '#56d364' : pilot.ehp_ratio >= 0.5 ? '#f0883e' : '#f85149',
                  }}>
                    {(pilot.ehp_ratio * 100).toFixed(0)}%
                  </span>

                  {/* Missing Skills */}
                  <span style={{
                    textAlign: 'right',
                    fontFamily: 'monospace',
                    fontSize: '0.78rem',
                    color: pilot.missing_skills_count === 0 ? '#56d364' : '#f0883e',
                  }}>
                    {pilot.missing_skills_count}
                  </span>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
