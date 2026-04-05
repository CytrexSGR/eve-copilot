import { formatISKCompact } from '../../utils/format';

interface WarSummary {
  period_hours: number;
  total_kills: number;
  total_isk_destroyed: number;
  active_systems: number;
  capital_kills: number;
}

interface BattleContextProps {
  battleKills: number;
  battleISK: number;
  battleCapitalKills: number;
  warSummary: WarSummary | null;
}

export function BattleContext({ battleKills, battleISK, battleCapitalKills, warSummary }: BattleContextProps) {
  if (!warSummary || warSummary.total_kills === 0) return null;

  const killPct = (battleKills / warSummary.total_kills) * 100;
  const iskPct = warSummary.total_isk_destroyed > 0
    ? (battleISK / warSummary.total_isk_destroyed) * 100
    : 0;

  const significance = killPct >= 20 ? 'major' : killPct >= 10 ? 'notable' : killPct >= 5 ? 'moderate' : 'minor';
  const sigColor = significance === 'major' ? '#ff4444'
    : significance === 'notable' ? '#ff8800'
    : significance === 'moderate' ? '#ffcc00'
    : '#8b949e';

  return (
    <div style={{
      background: 'rgba(0,0,0,0.2)',
      borderRadius: '6px',
      border: `1px solid ${sigColor}30`,
      padding: '0.4rem 1rem',
      marginBottom: '0.75rem',
      display: 'flex',
      alignItems: 'center',
      gap: '1.5rem',
      flexWrap: 'wrap',
      fontSize: '0.7rem',
    }}>
      <span style={{
        padding: '0.15rem 0.4rem',
        borderRadius: '3px',
        background: `${sigColor}20`,
        color: sigColor,
        fontSize: '0.6rem',
        fontWeight: 700,
        textTransform: 'uppercase',
      }}>
        {significance}
      </span>

      <span style={{ color: '#c9d1d9' }}>
        <span style={{ color: sigColor, fontWeight: 700, fontFamily: 'monospace' }}>
          {killPct.toFixed(1)}%
        </span>
        <span style={{ color: '#8b949e' }}> of 24h kills</span>
      </span>

      <span style={{ color: '#c9d1d9' }}>
        <span style={{ color: sigColor, fontWeight: 700, fontFamily: 'monospace' }}>
          {iskPct.toFixed(1)}%
        </span>
        <span style={{ color: '#8b949e' }}> of 24h ISK ({formatISKCompact(warSummary.total_isk_destroyed)} total)</span>
      </span>

      {battleCapitalKills > 0 && warSummary.capital_kills > 0 && (
        <span style={{ color: '#ff8800' }}>
          <span style={{ fontWeight: 700, fontFamily: 'monospace' }}>{battleCapitalKills}</span>
          <span style={{ color: '#8b949e' }}> of {warSummary.capital_kills} capital kills today</span>
        </span>
      )}

      <span style={{ color: '#6e7681', marginLeft: 'auto', fontSize: '0.6rem' }}>
        24h: {warSummary.total_kills.toLocaleString()} kills across {warSummary.active_systems} systems
      </span>
    </div>
  );
}
