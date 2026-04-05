import { formatISKCompact } from '../../utils/format';

interface ResistEntry {
  avg: number;
  weakness: 'EXPLOIT' | 'SOFT' | 'NORMAL';
}

interface TopLoss {
  killmail_id: number;
  ship_name: string;
  ship_value: number;
  ehp: number;
  tank_type: string;
  resist_weakness: string;
}

export interface VictimTankAnalysis {
  battle_id: number;
  killmails_analyzed: number;
  tank_distribution: { shield: number; armor: number; hull: number };
  avg_ehp: number;
  resist_profile: {
    em: ResistEntry;
    thermal: ResistEntry;
    kinetic: ResistEntry;
    explosive: ResistEntry;
  };
  top_losses: TopLoss[];
}

interface BattleVictimTankProps {
  data: VictimTankAnalysis | null;
}

const DAMAGE_COLORS: Record<string, string> = {
  em: '#00d4ff',
  thermal: '#ff4444',
  kinetic: '#888888',
  explosive: '#ff8800',
};

const DAMAGE_LABELS: Record<string, string> = {
  em: 'EM',
  thermal: 'Thermal',
  kinetic: 'Kinetic',
  explosive: 'Explosive',
};

const WEAKNESS_COLORS: Record<string, string> = {
  EXPLOIT: '#f85149',
  SOFT: '#d29922',
  NORMAL: '#3fb950',
};

const TANK_COLORS: Record<string, string> = {
  shield: '#00d4ff',
  armor: '#ff8800',
  hull: '#8b949e',
};

export function BattleVictimTank({ data }: BattleVictimTankProps) {
  if (!data || data.killmails_analyzed === 0) return null;

  const resistEntries = Object.entries(data.resist_profile)
    .map(([type, entry]) => ({ type, ...entry }))
    .sort((a, b) => a.avg - b.avg); // Weakest first

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '8px',
      border: '1px solid rgba(255,255,255,0.08)',
      marginBottom: '1rem',
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '0.5rem 1rem',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem',
      }}>
        <span style={{
          padding: '0.15rem 0.5rem',
          borderRadius: '4px',
          background: 'rgba(168, 85, 247, 0.15)',
          color: '#a855f7',
          fontSize: '0.7rem',
          fontWeight: 700,
        }}>
          VICTIM TANK ANALYSIS
        </span>
        <span style={{ color: '#8b949e', fontSize: '0.65rem' }}>
          {data.killmails_analyzed} ships analyzed
        </span>
        <span style={{ color: '#c9d1d9', fontSize: '0.75rem', fontWeight: 700, fontFamily: 'monospace', marginLeft: 'auto' }}>
          {data.avg_ehp.toLocaleString()} EHP avg
        </span>
      </div>

      {/* Content: 2-column */}
      <div style={{
        padding: '0.75rem 1rem',
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '1.5rem',
      }}>
        {/* Left: Tank Distribution */}
        <div>
          <div style={{ fontSize: '0.65rem', color: '#8b949e', marginBottom: '0.5rem', fontWeight: 600 }}>
            TANK TYPE DISTRIBUTION
          </div>
          {(['shield', 'armor', 'hull'] as const).map((type) => {
            const pct = data.tank_distribution[type];
            if (pct === 0) return null;
            return (
              <div key={type} style={{ marginBottom: '0.35rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.15rem' }}>
                  <span style={{ color: TANK_COLORS[type], fontSize: '0.65rem', fontWeight: 600, textTransform: 'capitalize' }}>
                    {type}
                  </span>
                  <span style={{ color: '#c9d1d9', fontSize: '0.65rem', fontFamily: 'monospace' }}>
                    {pct.toFixed(1)}%
                  </span>
                </div>
                <div style={{ height: '4px', background: 'rgba(255,255,255,0.08)', borderRadius: '2px', overflow: 'hidden' }}>
                  <div style={{
                    width: `${pct}%`,
                    height: '100%',
                    background: TANK_COLORS[type],
                    borderRadius: '2px',
                    transition: 'width 0.3s',
                  }} />
                </div>
              </div>
            );
          })}
        </div>

        {/* Right: Resist Weaknesses */}
        <div>
          <div style={{ fontSize: '0.65rem', color: '#8b949e', marginBottom: '0.5rem', fontWeight: 600 }}>
            RESIST PROFILE (weakest first)
          </div>
          {resistEntries.map((entry) => (
            <div key={entry.type} style={{ marginBottom: '0.35rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.15rem' }}>
                <span style={{ color: DAMAGE_COLORS[entry.type], fontSize: '0.65rem', fontWeight: 600, width: '55px' }}>
                  {DAMAGE_LABELS[entry.type]}
                </span>
                <span style={{ color: '#c9d1d9', fontSize: '0.65rem', fontFamily: 'monospace', width: '40px', textAlign: 'right' }}>
                  {entry.avg.toFixed(1)}%
                </span>
                <span style={{
                  padding: '0.05rem 0.25rem',
                  borderRadius: '2px',
                  fontSize: '0.5rem',
                  fontWeight: 700,
                  background: `${WEAKNESS_COLORS[entry.weakness]}20`,
                  color: WEAKNESS_COLORS[entry.weakness],
                }}>
                  {entry.weakness}
                </span>
              </div>
              <div style={{ height: '3px', background: 'rgba(255,255,255,0.08)', borderRadius: '2px', overflow: 'hidden' }}>
                <div style={{
                  width: `${entry.avg}%`,
                  height: '100%',
                  background: DAMAGE_COLORS[entry.type],
                  opacity: 0.6,
                  borderRadius: '2px',
                }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Top Losses with EHP */}
      {data.top_losses.length > 0 && (
        <div style={{
          padding: '0.5rem 1rem',
          borderTop: '1px solid rgba(255,255,255,0.06)',
          background: 'rgba(0,0,0,0.15)',
        }}>
          <div style={{ fontSize: '0.6rem', color: '#6e7681', marginBottom: '0.3rem' }}>
            HIGH-VALUE LOSSES (by EHP)
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            {data.top_losses.map((loss) => (
              <a
                key={loss.killmail_id}
                href={`https://zkillboard.com/kill/${loss.killmail_id}/`}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  padding: '0.2rem 0.5rem',
                  borderRadius: '3px',
                  background: 'rgba(255,255,255,0.05)',
                  border: `1px solid ${TANK_COLORS[loss.tank_type] || '#8b949e'}30`,
                  fontSize: '0.6rem',
                  color: '#c9d1d9',
                  textDecoration: 'none',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                }}
              >
                <span style={{ fontWeight: 600 }}>{loss.ship_name}</span>
                <span style={{ color: TANK_COLORS[loss.tank_type], fontFamily: 'monospace', fontSize: '0.55rem' }}>
                  {loss.ehp.toLocaleString()} EHP
                </span>
                <span style={{ color: '#ff8800', fontFamily: 'monospace', fontSize: '0.55rem' }}>
                  {formatISKCompact(loss.ship_value)}
                </span>
                <span style={{
                  padding: '0.02rem 0.15rem',
                  borderRadius: '2px',
                  fontSize: '0.45rem',
                  fontWeight: 700,
                  background: '#f8514920',
                  color: '#f85149',
                }}>
                  {'\u25BC'}{loss.resist_weakness}
                </span>
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
