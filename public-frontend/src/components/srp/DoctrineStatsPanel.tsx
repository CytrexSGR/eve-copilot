import { useState, useEffect } from 'react';
import { doctrineStatsApi, doctrineApi } from '../../services/api/srp';
import type { DoctrineStats, DoctrineAutoPrice } from '../../types/srp';
import { formatIsk } from '../../types/srp';

function formatCompact(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}k`;
  return String(Math.round(value));
}

function formatSpeed(value: number): string {
  return Math.round(value).toLocaleString('en-US');
}

export function DoctrineStatsPanel({ doctrineId }: { doctrineId: number }) {
  const [stats, setStats] = useState<DoctrineStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [price, setPrice] = useState<DoctrineAutoPrice | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(false);
    doctrineStatsApi.getStats(doctrineId)
      .then((data: DoctrineStats) => {
        if (!cancelled) setStats(data);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [doctrineId]);

  useEffect(() => {
    let cancelled = false;
    doctrineApi.getPrice(doctrineId)
      .then((data: DoctrineAutoPrice) => {
        if (!cancelled) setPrice(data);
      })
      .catch(() => {
        // Silently ignore price fetch errors — badge simply won't show
      });
    return () => { cancelled = true; };
  }, [doctrineId]);

  if (error || (!loading && !stats)) return null;

  if (loading) {
    return (
      <div style={{
        display: 'flex', gap: '0.5rem', alignItems: 'center',
        padding: '0.4rem 0', marginBottom: '0.5rem',
      }}>
        {[80, 70, 60, 55, 70, 90].map((w, i) => (
          <div key={i} style={{
            width: `${w}px`, height: '20px', borderRadius: '4px',
            background: 'rgba(255,255,255,0.05)',
            animation: 'pulse 1.5s ease-in-out infinite',
          }} />
        ))}
      </div>
    );
  }

  if (!stats) return null;

  const tankColor = stats.defense.tank_type === 'shield' ? '#00d4ff' : '#ff8800';
  const tankLabel = stats.defense.tank_type === 'shield' ? 'SHIELD' : 'ARMOR';
  const capColor = stats.capacitor.stable ? '#3fb950' : '#d29922';
  const capLabel = stats.capacitor.stable ? 'STABLE' : 'UNSTABLE';

  const badgeStyle = (color: string): React.CSSProperties => ({
    display: 'inline-flex', alignItems: 'center', gap: '0.3rem',
    padding: '0.15rem 0.5rem', borderRadius: '4px', fontSize: '0.75rem',
    fontWeight: 600, fontFamily: 'monospace',
    background: `${color}15`, border: `1px solid ${color}40`, color,
    whiteSpace: 'nowrap',
  });

  return (
    <div style={{
      display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap',
      padding: '0.4rem 0', marginBottom: '0.5rem',
    }}>
      <span style={badgeStyle('#d29922')}>
        {Math.round(stats.offense.total_dps)} DPS
      </span>
      <span style={badgeStyle('#00d4ff')}>
        {formatCompact(stats.defense.total_ehp)} EHP
      </span>
      <span style={badgeStyle(tankColor)}>
        {tankLabel}
      </span>
      <span style={badgeStyle(capColor)}>
        {capLabel}
      </span>
      <span style={badgeStyle('rgba(255,255,255,0.5)')}>
        {formatSpeed(stats.navigation.max_velocity)} m/s
      </span>
      {price && (
        <span style={badgeStyle('#f0883e')}>
          {formatIsk(price.total_price)} Jita
        </span>
      )}
    </div>
  );
}
