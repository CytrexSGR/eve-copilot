import { MiniSparkline } from './MiniSparkline';
import { AllianceLink } from '../AllianceLink';
import { COLORS, ISK_BILLION, MAX_POWER_ENTRIES } from '../../constants';

interface PowerEntry {
  name: string;
  alliance_id?: number;
  kills?: number;
  losses?: number;
  net_isk?: number;
  efficiency?: number;
  pilots?: number;
  isk_destroyed?: number;
  isk_lost?: number;
  isk_per_pilot?: number;
  trend_24h?: number | null;
  history_7d?: number[];
}

interface PowerListProps {
  entries: (PowerEntry | string)[];
  type: 'rising' | 'falling';
  maxEntries?: number;
}

export function PowerList({ entries, type, maxEntries = MAX_POWER_ENTRIES }: PowerListProps) {
  const isRising = type === 'rising';
  const color = isRising ? COLORS.positive : COLORS.negative;
  const title = isRising ? 'Rising Powers' : 'Falling Powers';

  const validEntries = entries
    .filter((e): e is PowerEntry => typeof e !== 'string')
    .slice(0, maxEntries);

  if (validEntries.length === 0) return null;

  return (
    <div>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.35rem',
        marginBottom: '0.25rem',
      }}>
        <span style={{
          width: 5, height: 5, borderRadius: '50%',
          background: color,
        }} />
        <span style={{
          fontSize: '0.6rem', color, fontWeight: 700,
          textTransform: 'uppercase',
        }}>
          {title}
        </span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.15rem' }}>
        {validEntries.map((entry, idx) => {
          const netIsk = (entry.net_isk || 0) / ISK_BILLION;
          const rawEff = entry.efficiency ?? (
            (entry.kills && entry.losses !== undefined)
              ? entry.kills / (entry.kills + (entry.losses || 0)) * 100
              : null
          );
          const efficiency = rawEff !== null ? Math.round(rawEff) : null;
          const effColor = efficiency !== null
            ? efficiency >= 60 ? '#3fb950' : efficiency >= 40 ? '#d29922' : '#f85149'
            : 'rgba(255,255,255,0.3)';

          return (
            <div
              key={entry.alliance_id || `${entry.name}-${idx}`}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.35rem',
                padding: '0.25rem 0.4rem',
                background: `${color}08`,
                borderRadius: '4px',
                borderLeft: `2px solid ${color}`,
              }}
            >
              {entry.alliance_id && (
                <img
                  src={`https://images.evetech.net/alliances/${entry.alliance_id}/logo?size=32`}
                  alt="" width={18} height={18}
                  style={{ borderRadius: '3px', background: 'rgba(0,0,0,0.3)', flexShrink: 0 }}
                  onError={(e) => { e.currentTarget.style.display = 'none'; }}
                />
              )}

              <div style={{ flex: 1, minWidth: 0 }}>
                {entry.alliance_id ? (
                  <AllianceLink
                    allianceId={entry.alliance_id}
                    name={entry.name}
                    style={{ fontWeight: 600, fontSize: '0.65rem' }}
                  />
                ) : (
                  <span style={{
                    fontWeight: 600, fontSize: '0.65rem',
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    display: 'block',
                  }}>
                    {entry.name}
                  </span>
                )}
              </div>

              {entry.pilots != null && entry.pilots > 0 && (
                <span style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.3)', fontFamily: 'monospace' }}>
                  {entry.pilots}p
                </span>
              )}

              <span style={{ fontSize: '0.55rem', color: '#00ff88', fontFamily: 'monospace', fontWeight: 600 }}>
                {entry.kills ?? 0}
              </span>
              <span style={{ fontSize: '0.45rem', color: 'rgba(255,255,255,0.15)' }}>/</span>
              <span style={{ fontSize: '0.55rem', color: '#ff4444', fontFamily: 'monospace', fontWeight: 600 }}>
                {entry.losses ?? 0}
              </span>

              {entry.history_7d && entry.history_7d.length >= 2 && (
                <MiniSparkline
                  data={entry.history_7d}
                  width={36}
                  height={12}
                  color={color}
                  showTrend={false}
                />
              )}

              {efficiency !== null && (
                <span style={{
                  fontSize: '0.55rem', fontWeight: 700, color: effColor,
                  fontFamily: 'monospace', minWidth: '22px', textAlign: 'right',
                }}>
                  {efficiency}%
                </span>
              )}

              <span style={{
                fontSize: '0.6rem', fontWeight: 700, color,
                fontFamily: 'monospace', minWidth: '40px', textAlign: 'right',
              }}>
                {isRising ? '+' : ''}{netIsk.toFixed(1)}B
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
