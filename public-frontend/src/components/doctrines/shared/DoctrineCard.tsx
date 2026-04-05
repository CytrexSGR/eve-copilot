import { memo } from 'react';
import { EfficiencyBar } from './EfficiencyBar';

interface DoctrineMetrics {
  iskEfficiency: number;
  kdRatio: number;
  winRate: number;
  survivalRate: number;
}

interface DoctrineCardProps {
  name: string;
  rank?: number;
  metrics: DoctrineMetrics;
  color?: string;
}

export const DoctrineCard = memo(function DoctrineCard({
  name,
  rank,
  metrics,
  color = '#ff4444'
}: DoctrineCardProps) {
  return (
    <div style={{
      padding: '0.75rem',
      background: `${color}08`,
      borderRadius: '8px',
      borderLeft: `3px solid ${color}`
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
        {rank !== undefined && (
          <span style={{
            fontFamily: 'monospace',
            fontSize: '0.7rem',
            color,
            fontWeight: 700,
            minWidth: '1.5rem'
          }}>
            #{rank}
          </span>
        )}
        <span style={{ fontSize: '0.9rem', fontWeight: 600, color: '#fff' }}>
          {name}
        </span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
        <EfficiencyBar value={metrics.iskEfficiency} label="ISK Eff" />
        <div style={{ display: 'flex', gap: '1rem', fontSize: '0.7rem' }}>
          <span>
            <span style={{ color: 'rgba(255,255,255,0.5)' }}>K/D </span>
            <span style={{ color: '#00d4ff', fontFamily: 'monospace', fontWeight: 600 }}>
              {metrics.kdRatio.toFixed(1)}:1
            </span>
          </span>
          <span>
            <span style={{ color: 'rgba(255,255,255,0.5)' }}>Win </span>
            <span style={{ color: '#a855f7', fontFamily: 'monospace', fontWeight: 600 }}>
              {metrics.winRate}%
            </span>
          </span>
          <span>
            <span style={{ color: 'rgba(255,255,255,0.5)' }}>Surv </span>
            <span style={{ color: '#00ff88', fontFamily: 'monospace', fontWeight: 600 }}>
              {metrics.survivalRate}%
            </span>
          </span>
        </div>
      </div>
    </div>
  );
});
