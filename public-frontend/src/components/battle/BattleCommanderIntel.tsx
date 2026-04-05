import { formatISKCompact } from '../../utils/format';
import type { CommanderIntelResponse } from '../../services/api';

interface Killmail {
  killmail_id: number;
  is_solo: boolean;
  is_npc: boolean;
}

interface SystemDanger {
  system_id: number;
  danger_score: number;
  kills_24h: number;
  is_dangerous: boolean;
}

interface BattleCommanderIntelProps {
  commanderIntel: CommanderIntelResponse;
  recentKills: Killmail[];
  systemDanger: SystemDanger | null;
}

// CSS for animations
const STYLES = `
  @keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(1.2); }
  }
`;

export function BattleCommanderIntel({ commanderIntel, recentKills, systemDanger }: BattleCommanderIntelProps) {
  const { summary, top_killers, high_value_losses, capitals } = commanderIntel;

  // Calculate total high value ISK
  const totalHighValueIsk = high_value_losses.reduce((sum, l) => sum + l.value, 0);
  const totalCapitalLossIsk = capitals.lost.reduce((sum, c) => sum + c.value, 0);

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '8px',
      border: '1px solid rgba(255,255,255,0.08)',
      overflow: 'hidden',
      marginBottom: '1rem',
    }}>
      <style>{STYLES}</style>

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
            background: summary.capital_engagement ? '#ff8800' : '#00d4ff',
            animation: summary.super_escalation ? 'pulse 1.5s infinite' : 'none',
          }} />
          <span style={{
            fontSize: '0.75rem',
            fontWeight: 700,
            color: summary.capital_engagement ? '#ff8800' : '#00d4ff',
            textTransform: 'uppercase'
          }}>
            Commander Intel
          </span>

          {/* Status Badges */}
          <div style={{ display: 'flex', gap: '0.35rem', marginLeft: '0.5rem' }}>
            {summary.super_escalation && (
              <span style={{
                padding: '2px 6px',
                borderRadius: '3px',
                background: 'rgba(255, 68, 68, 0.3)',
                color: '#ff4444',
                fontSize: '0.6rem',
                fontWeight: 700,
                animation: 'pulse 1.5s infinite',
              }}>
                SUPERS
              </span>
            )}
            {summary.capital_engagement && !summary.super_escalation && (
              <span style={{
                padding: '2px 6px',
                borderRadius: '3px',
                background: 'rgba(255, 136, 0, 0.3)',
                color: '#ff8800',
                fontSize: '0.6rem',
                fontWeight: 700,
              }}>
                CAPITALS
              </span>
            )}
          </div>
        </div>

        {/* Summary Stats */}
        <div style={{ display: 'flex', gap: '1rem', fontSize: '0.65rem' }}>
          <span>
            <span style={{ color: '#00ff88', fontWeight: 700, fontFamily: 'monospace' }}>
              {summary.total_kills}
            </span>
            <span style={{ color: 'rgba(255,255,255,0.4)', marginLeft: '0.25rem' }}>kills</span>
          </span>
          <span>
            <span style={{ color: '#ffcc00', fontWeight: 700, fontFamily: 'monospace' }}>
              {formatISKCompact(summary.total_isk)}
            </span>
            <span style={{ color: 'rgba(255,255,255,0.4)', marginLeft: '0.25rem' }}>ISK</span>
          </span>
          {summary.high_value_count > 0 && (
            <span>
              <span style={{ color: '#ff4444', fontWeight: 700, fontFamily: 'monospace' }}>
                {summary.high_value_count}
              </span>
              <span style={{ color: 'rgba(255,255,255,0.4)', marginLeft: '0.25rem' }}>HVT</span>
            </span>
          )}
        </div>
      </div>

      {/* Content Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
        gap: '0.3rem',
        padding: '0.4rem',
      }}>
        {/* Combat Analysis - First */}
        <CombatAnalysisSection recentKills={recentKills} systemDanger={systemDanger} />

        {/* Top Killers */}
        {top_killers.length > 0 && (
          <TopKillersSection killers={top_killers} />
        )}

        {/* High-Value Losses */}
        {high_value_losses.length > 0 && (
          <HighValueLossesSection losses={high_value_losses} totalIsk={totalHighValueIsk} />
        )}

        {/* Capital Ships */}
        {capitals.has_capitals && (
          <CapitalsSection capitals={capitals} totalIsk={totalCapitalLossIsk} />
        )}
      </div>
    </div>
  );
}

// ============================================
// TOP KILLERS SECTION
// ============================================

interface TopKiller {
  character_id: number;
  character_name: string;
  kills: number;
  isk_destroyed: number;
  corporation_name: string | null;
  corporation_ticker: string | null;
  alliance_name: string;
  coalition_name: string | null;
}

function TopKillersSection({ killers }: { killers: TopKiller[] }) {
  return (
    <div style={{
      background: 'rgba(0,0,0,0.2)',
      borderRadius: '6px',
      overflow: 'hidden',
    }}>
      {/* Section Header */}
      <div style={{
        padding: '0.4rem 0.5rem',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          <span style={{ width: '5px', height: '5px', borderRadius: '50%', background: '#00ff88' }} />
          <span style={{ fontSize: '0.65rem', fontWeight: 700, color: '#00ff88', textTransform: 'uppercase' }}>
            Top Killers
          </span>
        </div>
        <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)' }}>
          {killers.length} pilots
        </span>
      </div>

      {/* Killers List */}
      <div style={{ padding: '0.35rem' }}>
        {killers.slice(0, 5).map((killer, idx) => {
          const isTop = idx === 0;
          const borderColor = isTop ? '#ffd700' : idx === 1 ? '#c0c0c0' : idx === 2 ? '#cd7f32' : 'rgba(0, 255, 136, 0.3)';

          return (
            <a
              key={killer.character_id}
              href={`https://zkillboard.com/character/${killer.character_id}/`}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: 'block',
                padding: '0.25rem 0.4rem',
                marginBottom: idx < 4 ? '0.15rem' : 0,
                background: isTop ? 'rgba(255, 215, 0, 0.1)' : `${borderColor}10`,
                borderRadius: '4px',
                borderLeft: `2px solid ${borderColor}`,
                textDecoration: 'none',
                transition: 'all 0.15s ease',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.08)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = isTop ? 'rgba(255, 215, 0, 0.1)' : `${borderColor}10`; }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                {/* Rank */}
                <span style={{
                  fontSize: '0.6rem',
                  fontWeight: 800,
                  color: borderColor,
                  width: '18px',
                  textAlign: 'center',
                }}>
                  {isTop ? '👑' : `#${idx + 1}`}
                </span>

                {/* Character Portrait */}
                <img
                  src={`https://images.evetech.net/characters/${killer.character_id}/portrait?size=64`}
                  alt=""
                  loading="lazy"
                  decoding="async"
                  style={{ width: 24, height: 24, borderRadius: '3px', background: 'rgba(0,0,0,0.3)' }}
                  onError={(e) => { e.currentTarget.style.display = 'none'; }}
                />

                {/* Name + Corp */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {killer.character_name}
                  </div>
                  <div style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.4)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {killer.corporation_ticker && `[${killer.corporation_ticker}]`}
                    {killer.alliance_name && killer.alliance_name !== 'No Alliance' && ` ${killer.alliance_name}`}
                    {killer.coalition_name && <span style={{ color: '#a855f7' }}> • {killer.coalition_name}</span>}
                  </div>
                </div>

                {/* Stats */}
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#00ff88', fontFamily: 'monospace' }}>
                    {killer.kills}K
                  </div>
                  <div style={{ fontSize: '0.55rem', color: '#ffcc00', fontFamily: 'monospace' }}>
                    {formatISKCompact(killer.isk_destroyed)}
                  </div>
                </div>
              </div>
            </a>
          );
        })}
      </div>
    </div>
  );
}

// ============================================
// HIGH-VALUE LOSSES SECTION
// ============================================

interface HighValueLoss {
  killmail_id: number;
  ship_name: string;
  ship_class: string;
  value: number;
  pilot_name: string;
  corporation_ticker: string | null;
  alliance_name: string;
}

function HighValueLossesSection({ losses, totalIsk }: { losses: HighValueLoss[]; totalIsk: number }) {
  return (
    <div style={{
      background: 'rgba(0,0,0,0.2)',
      borderRadius: '6px',
      overflow: 'hidden',
    }}>
      {/* Section Header */}
      <div style={{
        padding: '0.4rem 0.5rem',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          <span style={{ width: '5px', height: '5px', borderRadius: '50%', background: '#ff4444' }} />
          <span style={{ fontSize: '0.65rem', fontWeight: 700, color: '#ff4444', textTransform: 'uppercase' }}>
            High-Value Losses
          </span>
        </div>
        <span style={{ fontSize: '0.6rem', color: '#ff4444', fontFamily: 'monospace', fontWeight: 700 }}>
          {formatISKCompact(totalIsk)}
        </span>
      </div>

      {/* Losses List */}
      <div style={{ padding: '0.35rem' }}>
        {losses.slice(0, 5).map((loss, idx) => {
          // Color based on value
          const valueColor = loss.value >= 10e9 ? '#ff4444' : loss.value >= 1e9 ? '#ff8800' : '#ffcc00';

          return (
            <a
              key={loss.killmail_id}
              href={`https://zkillboard.com/kill/${loss.killmail_id}/`}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: 'block',
                padding: '0.25rem 0.4rem',
                marginBottom: idx < 4 ? '0.15rem' : 0,
                background: `${valueColor}08`,
                borderRadius: '4px',
                borderLeft: `2px solid ${valueColor}`,
                textDecoration: 'none',
                transition: 'all 0.15s ease',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.08)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = `${valueColor}08`; }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                {/* Ship Name + Class */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                    <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#fff' }}>
                      {loss.ship_name}
                    </span>
                    {loss.ship_class && (
                      <span style={{
                        fontSize: '0.5rem',
                        padding: '1px 4px',
                        background: 'rgba(255,255,255,0.1)',
                        borderRadius: '2px',
                        color: 'rgba(255,255,255,0.5)',
                      }}>
                        {loss.ship_class}
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.4)' }}>
                    {loss.pilot_name}
                    {loss.corporation_ticker && ` [${loss.corporation_ticker}]`}
                    {loss.alliance_name && loss.alliance_name !== 'No Alliance' && ` • ${loss.alliance_name}`}
                  </div>
                </div>

                {/* Value */}
                <div style={{ fontSize: '0.8rem', fontWeight: 700, color: valueColor, fontFamily: 'monospace' }}>
                  {formatISKCompact(loss.value)}
                </div>
              </div>
            </a>
          );
        })}
      </div>
    </div>
  );
}

// ============================================
// CAPITALS SECTION
// ============================================

interface Capitals {
  has_capitals: boolean;
  lost: { ship_name: string; count: number; value: number; alliance_name?: string; alliance_id?: number | null }[];
  on_field: { ship_name: string; alliance_name?: string; alliance_id?: number | null }[];
}

function CapitalsSection({ capitals, totalIsk }: { capitals: Capitals; totalIsk: number }) {
  const uniqueOnField = [...new Set(capitals.on_field.map(c => c.ship_name))];
  const hasSupers = capitals.lost.some(c =>
    c.ship_name.includes('Titan') || c.ship_name.includes('Supercarrier') ||
    c.ship_name.includes('Aeon') || c.ship_name.includes('Hel') ||
    c.ship_name.includes('Nyx') || c.ship_name.includes('Wyvern') ||
    c.ship_name.includes('Avatar') || c.ship_name.includes('Erebus') ||
    c.ship_name.includes('Ragnarok') || c.ship_name.includes('Leviathan')
  );

  const headerColor = hasSupers ? '#ff4444' : '#ff8800';

  return (
    <div style={{
      background: 'rgba(0,0,0,0.2)',
      borderRadius: '6px',
      overflow: 'hidden',
    }}>
      {/* Section Header */}
      <div style={{
        padding: '0.4rem 0.5rem',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          <span style={{ width: '5px', height: '5px', borderRadius: '50%', background: headerColor }} />
          <span style={{ fontSize: '0.65rem', fontWeight: 700, color: headerColor, textTransform: 'uppercase' }}>
            Capital Ships
          </span>
          {hasSupers && (
            <span style={{
              padding: '1px 4px',
              borderRadius: '2px',
              background: 'rgba(255, 68, 68, 0.3)',
              color: '#ff4444',
              fontSize: '0.5rem',
              fontWeight: 700,
            }}>
              SUPERS
            </span>
          )}
        </div>
        {totalIsk > 0 && (
          <span style={{ fontSize: '0.6rem', color: '#ff4444', fontFamily: 'monospace', fontWeight: 700 }}>
            -{formatISKCompact(totalIsk)}
          </span>
        )}
      </div>

      {/* Content */}
      <div style={{ padding: '0.35rem' }}>
        {/* Lost Capitals */}
        {capitals.lost.length > 0 && (
          <div style={{ marginBottom: uniqueOnField.length > 0 ? '0.5rem' : 0 }}>
            <div style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.4)', padding: '0.15rem 0.35rem', textTransform: 'uppercase' }}>
              Destroyed
            </div>
            {capitals.lost.slice(0, 5).map((cap, idx) => {
              const isSuper = cap.ship_name.includes('Titan') || cap.ship_name.includes('Supercarrier') ||
                cap.ship_name.includes('Aeon') || cap.ship_name.includes('Hel') ||
                cap.ship_name.includes('Nyx') || cap.ship_name.includes('Wyvern') ||
                cap.ship_name.includes('Avatar') || cap.ship_name.includes('Erebus') ||
                cap.ship_name.includes('Ragnarok') || cap.ship_name.includes('Leviathan');
              const borderColor = isSuper ? '#ff4444' : '#ff8800';

              return (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '0.25rem 0.4rem',
                    marginBottom: '0.15rem',
                    background: `${borderColor}10`,
                    borderRadius: '4px',
                    borderLeft: `2px solid ${borderColor}`,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                    <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#fff' }}>
                      {cap.ship_name}
                    </span>
                    {cap.count > 1 && (
                      <span style={{ fontSize: '0.6rem', color: borderColor, fontWeight: 700 }}>
                        x{cap.count}
                      </span>
                    )}
                  </div>
                  <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#ff4444', fontFamily: 'monospace' }}>
                    {formatISKCompact(cap.value)}
                  </span>
                </div>
              );
            })}
          </div>
        )}

        {/* On Field */}
        {uniqueOnField.length > 0 && (
          <div>
            <div style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.4)', padding: '0.15rem 0.35rem', textTransform: 'uppercase' }}>
              On Field
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem', padding: '0.25rem' }}>
              {uniqueOnField.slice(0, 8).map((ship, idx) => (
                <span key={idx} style={{
                  padding: '3px 8px',
                  background: 'rgba(255, 136, 0, 0.15)',
                  borderRadius: '3px',
                  fontSize: '0.65rem',
                  color: '#ff8800',
                  fontWeight: 600,
                }}>
                  {ship}
                </span>
              ))}
              {uniqueOnField.length > 8 && (
                <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)', padding: '3px' }}>
                  +{uniqueOnField.length - 8} more
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================
// COMBAT ANALYSIS SECTION
// ============================================

function CombatAnalysisSection({ recentKills, systemDanger }: { recentKills: Killmail[]; systemDanger: SystemDanger | null }) {
  const soloKills = recentKills.filter(k => k.is_solo).length;
  const fleetKills = recentKills.filter(k => !k.is_solo && !k.is_npc).length;
  const npcKills = recentKills.filter(k => k.is_npc).length;
  const totalKills = recentKills.length;

  return (
    <div style={{
      background: 'rgba(0,0,0,0.2)',
      borderRadius: '6px',
      overflow: 'hidden',
    }}>
      {/* Section Header */}
      <div style={{
        padding: '0.4rem 0.5rem',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          <span style={{ width: '5px', height: '5px', borderRadius: '50%', background: '#00d4ff' }} />
          <span style={{ fontSize: '0.65rem', fontWeight: 700, color: '#00d4ff', textTransform: 'uppercase' }}>
            Combat Analysis
          </span>
        </div>
        <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)' }}>
          {totalKills} kills analyzed
        </span>
      </div>

      {/* Stats Grid */}
      <div style={{ padding: '0.35rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.2rem', marginBottom: '0.35rem' }}>
          <StatBox label="Solo Kills" value={soloKills} color="#00d4ff" />
          <StatBox label="Fleet Kills" value={fleetKills} color="#ff4444" />
          <StatBox label="NPC Kills" value={npcKills} color="#ffcc00" />
          <StatBox label="24h System" value={systemDanger?.kills_24h || 0} color="#00ff88" />
        </div>

        {/* Kill Type Distribution Bar */}
        {totalKills > 0 && (
          <div>
            <div style={{ display: 'flex', height: '18px', borderRadius: '3px', overflow: 'hidden', marginBottom: '0.3rem' }}>
              {soloKills > 0 && (
                <div style={{
                  width: `${(soloKills / totalKills) * 100}%`,
                  background: '#00d4ff',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '0.6rem',
                  fontWeight: 700,
                  color: 'white'
                }}>
                  {soloKills > 2 && soloKills}
                </div>
              )}
              {fleetKills > 0 && (
                <div style={{
                  width: `${(fleetKills / totalKills) * 100}%`,
                  background: '#ff4444',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '0.6rem',
                  fontWeight: 700,
                  color: 'white'
                }}>
                  {fleetKills > 2 && fleetKills}
                </div>
              )}
              {npcKills > 0 && (
                <div style={{
                  width: `${(npcKills / totalKills) * 100}%`,
                  background: '#ffcc00',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '0.6rem',
                  fontWeight: 700,
                  color: 'rgba(0,0,0,0.8)'
                }}>
                  {npcKills > 2 && npcKills}
                </div>
              )}
            </div>
            <div style={{ display: 'flex', gap: '0.75rem', fontSize: '0.55rem', color: 'rgba(255,255,255,0.5)' }}>
              <span><span style={{ color: '#00d4ff' }}>●</span> Solo</span>
              <span><span style={{ color: '#ff4444' }}>●</span> Fleet</span>
              <span><span style={{ color: '#ffcc00' }}>●</span> NPC</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function StatBox({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div style={{
      padding: '0.3rem 0.4rem',
      background: `${color}10`,
      borderRadius: '4px',
      borderLeft: `2px solid ${color}`,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
    }}>
      <span style={{ fontSize: '0.55rem', color: 'rgba(255,255,255,0.5)' }}>{label}</span>
      <span style={{ fontSize: '0.75rem', fontWeight: 700, color, fontFamily: 'monospace' }}>{value}</span>
    </div>
  );
}
