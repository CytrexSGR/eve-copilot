import { formatISK } from '../../utils/format';

interface CombatSummary {
  total_kills: number;
  total_isk_destroyed: number;
  active_systems: number;
  capital_kills: number;
}

interface EconomySummaryBarProps {
  summary: CombatSummary | null;
}

export function EconomySummaryBar({ summary }: EconomySummaryBarProps) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '0.25rem',
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '6px',
      border: '1px solid rgba(255,255,255,0.05)',
      padding: '0.35rem 0.5rem',
      height: '42px',
      boxSizing: 'border-box',
    }}>
      {/* Kills */}
      <div style={{ padding: '0.35rem 0.6rem', background: 'rgba(255,68,68,0.1)', borderRadius: '4px', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
        <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#ff4444', fontFamily: 'monospace' }}>
          {summary?.total_kills?.toLocaleString() || '—'}
        </span>
        <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.03em' }}>Kills</span>
      </div>

      {/* ISK */}
      <div style={{ padding: '0.35rem 0.6rem', background: 'rgba(255,204,0,0.1)', borderRadius: '4px', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
        <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#ffcc00', fontFamily: 'monospace' }}>
          {summary ? formatISK(summary.total_isk_destroyed) : '—'}
        </span>
        <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.03em' }}>ISK</span>
      </div>

      {/* Systems */}
      <div style={{ padding: '0.35rem 0.6rem', background: 'rgba(0,212,255,0.1)', borderRadius: '4px', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
        <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#00d4ff', fontFamily: 'monospace' }}>
          {summary?.active_systems || '—'}
        </span>
        <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.03em' }}>Sys</span>
      </div>

      {/* Capitals */}
      <div style={{ padding: '0.35rem 0.6rem', background: 'rgba(168,85,247,0.1)', borderRadius: '4px', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
        <span style={{
          fontSize: '0.75rem',
          fontWeight: 700,
          color: (summary?.capital_kills || 0) > 0 ? '#a855f7' : 'rgba(168,85,247,0.4)',
          fontFamily: 'monospace',
        }}>
          {summary?.capital_kills || 0}
        </span>
        <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: '0.03em' }}>Caps</span>
      </div>
    </div>
  );
}
