import { formatISKCompact } from '../../utils/format';

interface Killmail {
  killmail_id: number;
  killmail_time: string;
  solar_system_id: number;
  ship_type_id: number;
  ship_name?: string;
  ship_value: number;
  victim_character_id: number;
  victim_corporation_id: number;
  victim_alliance_id: number | null;
  attacker_count: number;
  is_solo: boolean;
  is_npc: boolean;
}

interface BattleKillFeedProps {
  kills: Killmail[];
  totalKills: number;
}

// EVE Image Server URLs
const EVE_IMAGE = {
  ship: (typeId: number, size = 32) => `https://images.evetech.net/types/${typeId}/render?size=${size}`,
  character: (id: number, size = 32) => `https://images.evetech.net/characters/${id}/portrait?size=${size}`,
  corp: (id: number, size = 32) => `https://images.evetech.net/corporations/${id}/logo?size=${size}`,
  alliance: (id: number, size = 32) => `https://images.evetech.net/alliances/${id}/logo?size=${size}`,
};

function formatTime(timeStr: string): string {
  const now = new Date();
  const then = new Date(timeStr);
  const diffMs = now.getTime() - then.getTime();
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return 'now';
  if (diffMins < 60) return `${diffMins}m`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h`;
  return `${Math.floor(diffHours / 24)}d`;
}

function getValueColor(value: number): string {
  if (value >= 1_000_000_000) return '#f85149'; // 1B+ red
  if (value >= 100_000_000) return '#ff8800';   // 100M+ orange
  if (value >= 10_000_000) return '#d29922';    // 10M+ yellow
  return 'rgba(255,255,255,0.7)';
}

export function BattleKillFeed({ kills, totalKills }: BattleKillFeedProps) {
  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      border: '1px solid rgba(255,255,255,0.08)',
      borderRadius: '8px',
      overflow: 'hidden',
      marginBottom: '1rem'
    }}>
      {/* Header */}
      <div style={{
        padding: '0.5rem 0.75rem',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            background: '#f85149',
          }} />
          <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#f85149', textTransform: 'uppercase' }}>
            Battle Killmails
          </span>
          <span style={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.6rem' }}>
            {kills.length} of {totalKills}
          </span>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', fontSize: '0.55rem' }}>
          <span style={{ color: '#58a6ff' }}>● SOLO</span>
          <span style={{ color: '#f85149' }}>● FLEET</span>
          <span style={{ color: '#d29922' }}>● NPC</span>
        </div>
      </div>

      {kills.length === 0 ? (
        <div style={{
          padding: '2rem',
          textAlign: 'center',
          color: 'rgba(255,255,255,0.4)'
        }}>
          <p style={{ fontSize: '0.85rem' }}>No killmail data available</p>
          <p style={{ fontSize: '0.75rem' }}>Battle reports {totalKills} kills</p>
        </div>
      ) : (
        <div style={{
          maxHeight: '350px',
          overflowY: 'auto',
          overflowX: 'hidden',
          padding: '0.3rem',
        }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.15rem' }}>
            {kills.slice(0, 100).map((kill) => (
              <a
                key={kill.killmail_id}
                href={`https://zkillboard.com/kill/${kill.killmail_id}/`}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.35rem',
                  padding: '0.25rem 0.4rem',
                  background: 'rgba(255,255,255,0.02)',
                  borderRadius: '4px',
                  borderLeft: `2px solid ${kill.is_solo ? '#58a6ff' : kill.is_npc ? '#d29922' : '#f85149'}`,
                  textDecoration: 'none',
                  color: 'inherit',
                  transition: 'background 0.15s'
                }}
                onMouseOver={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.05)'; }}
                onMouseOut={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.02)'; }}
              >
                {/* Ship Icon */}
                <img
                  src={EVE_IMAGE.ship(kill.ship_type_id, 64)}
                  alt=""
                  loading="lazy"
                  decoding="async"
                  style={{
                    width: '24px',
                    height: '24px',
                    borderRadius: '3px',
                    background: 'rgba(0,0,0,0.3)',
                    flexShrink: 0,
                  }}
                  onError={(e) => { e.currentTarget.style.display = 'none'; }}
                />

                {/* Ship Name & Time */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{
                    fontWeight: 600,
                    fontSize: '0.7rem',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis'
                  }}>
                    {kill.ship_name || `Ship #${kill.ship_type_id}`}
                  </div>
                  <div style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.4)' }}>
                    {formatTime(kill.killmail_time)} • {kill.attacker_count}atk
                  </div>
                </div>

                {/* Victim Icons (Corp + Alliance) */}
                <div style={{ display: 'flex', gap: '0.25rem', alignItems: 'center' }}>
                  {kill.victim_corporation_id && (
                    <img
                      src={EVE_IMAGE.corp(kill.victim_corporation_id, 32)}
                      alt=""
                      title="Corporation"
                      loading="lazy"
                      decoding="async"
                      style={{
                        width: '18px',
                        height: '18px',
                        borderRadius: '2px',
                        opacity: 0.8
                      }}
                      onError={(e) => { e.currentTarget.style.display = 'none'; }}
                    />
                  )}
                  {kill.victim_alliance_id && (
                    <img
                      src={EVE_IMAGE.alliance(kill.victim_alliance_id, 32)}
                      alt=""
                      title="Alliance"
                      loading="lazy"
                      decoding="async"
                      style={{
                        width: '18px',
                        height: '18px',
                        borderRadius: '2px',
                        opacity: 0.8
                      }}
                      onError={(e) => { e.currentTarget.style.display = 'none'; }}
                    />
                  )}
                </div>

                {/* Value */}
                <div style={{
                  fontSize: '0.65rem',
                  fontWeight: 600,
                  fontFamily: 'monospace',
                  color: getValueColor(kill.ship_value),
                  minWidth: '40px',
                  textAlign: 'right'
                }}>
                  {formatISKCompact(kill.ship_value)}
                </div>

                {/* Type Badge */}
                <div style={{
                  padding: '0.15rem 0.4rem',
                  borderRadius: '3px',
                  fontSize: '0.6rem',
                  fontWeight: 600,
                  minWidth: '36px',
                  textAlign: 'center',
                  background: kill.is_solo
                    ? 'rgba(88,166,255,0.2)'
                    : kill.is_npc
                    ? 'rgba(210,153,34,0.2)'
                    : 'rgba(248,81,73,0.2)',
                  color: kill.is_solo ? '#58a6ff' : kill.is_npc ? '#d29922' : '#f85149'
                }}>
                  {kill.is_solo ? 'SOLO' : kill.is_npc ? 'NPC' : 'FLEET'}
                </div>
              </a>
            ))}
          </div>

          {kills.length > 100 && (
            <div style={{
              padding: '0.75rem',
              textAlign: 'center',
              color: 'rgba(255,255,255,0.4)',
              fontSize: '0.7rem'
            }}>
              Showing 100 of {kills.length} kills
            </div>
          )}
        </div>
      )}
    </div>
  );
}
