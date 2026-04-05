import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { battleApi, reportsApi } from '../services/api';

interface ParticipantAlliance {
  alliance_id: number;
  alliance_name: string;
  kills: number;
  isk_destroyed: number;
  power_bloc?: string;
}

interface ParticipantCorp {
  corporation_id: number;
  corporation_name: string;
  alliance_id?: number;
  kills: number;
  isk_destroyed: number;
}

interface BattleDetails {
  battle_id: number;
  system_name: string;
  region_name: string;
  started_at: string;
  last_kill_at: string;
  total_kills: number;
  total_isk_destroyed: number;
  attackers: ParticipantAlliance[];
  defenders: ParticipantAlliance[];
  attacker_corps: ParticipantCorp[];
  defender_corps: ParticipantCorp[];
  top_ships: Array<{ ship_name: string; count: number }>;
}

// Cache for power bloc mapping
let powerBlocCache: Map<number, string> | null = null;

interface AllianceInfo {
  alliance_id: number;
  alliance_name: string;
  kills?: number;
  losses?: number;
  powerbloc?: string;
}

interface TelegramAlert {
  battle_id: number;
  system_name: string;
  region_name: string;
  security: number;
  alert_type: 'milestone' | 'new_battle' | 'ended' | 'unknown';
  milestone: number;
  total_kills: number;
  total_isk_destroyed: number;
  telegram_message_id: number;
  sent_at: string;
  status: 'active' | 'ended';
  attackers?: AllianceInfo[];
  victims?: AllianceInfo[];
}

interface NewsTickerProps {
  maxAlerts?: number;
  refreshInterval?: number;
}

/**
 * NewsTicker Component
 *
 * Horizontal scrolling news ticker showing all Telegram alerts
 */
export default function NewsTicker({ maxAlerts = 30, refreshInterval = 60000 }: NewsTickerProps) {
  const [alerts, setAlerts] = useState<TelegramAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [isPaused, setIsPaused] = useState(false);
  const [hoveredAlert, setHoveredAlert] = useState<TelegramAlert | null>(null);
  const [battleDetails, setBattleDetails] = useState<BattleDetails | null>(null);
  const [tooltipPos, setTooltipPos] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [detailsLoading, setDetailsLoading] = useState(false);
  const tickerRef = useRef<HTMLDivElement>(null);
  const hoverTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    fetchAlerts();
    fetchPowerBlocs();
    const interval = setInterval(fetchAlerts, refreshInterval);
    return () => clearInterval(interval);
  }, [maxAlerts, refreshInterval]);

  const fetchPowerBlocs = async () => {
    if (powerBlocCache) return; // Already cached
    try {
      const data = await reportsApi.getPowerBlocsLive(1440);
      const map = new Map<number, string>();
      for (const coalition of data.coalitions || []) {
        for (const member of coalition.members || []) {
          map.set(member.alliance_id, coalition.name);
        }
      }
      powerBlocCache = map;
    } catch (err) {
      console.error('Error fetching power blocs:', err);
    }
  };

  const fetchAlerts = async () => {
    try {
      const data = await battleApi.getRecentTelegramAlerts(maxAlerts);
      setAlerts(data.alerts || []);
      setLoading(false);
    } catch (err) {
      console.error('Error fetching alerts:', err);
      setLoading(false);
    }
  };

  const getAlertIcon = (alertType: string): string => {
    switch (alertType) {
      case 'milestone': return '🎯';
      case 'new_battle': return '⚠️';
      case 'ended': return '✅';
      default: return '📢';
    }
  };

  const getAlertLabel = (alert: TelegramAlert): string => {
    switch (alert.alert_type) {
      case 'milestone': return `${alert.milestone} KILLS`;
      case 'new_battle': return 'NEW';
      case 'ended': return 'ENDED';
      default: return 'UPDATE';
    }
  };

  const formatISK = (isk: number): string => {
    if (isk >= 1_000_000_000) return `${(isk / 1_000_000_000).toFixed(1)}B`;
    if (isk >= 1_000_000) return `${(isk / 1_000_000).toFixed(0)}M`;
    return `${isk.toLocaleString()}`;
  };

  const formatRelativeTime = (timestamp: string): string => {
    const now = new Date();
    const then = new Date(timestamp);
    const diffMs = now.getTime() - then.getTime();
    const diffMinutes = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));

    if (diffMinutes < 1) return 'now';
    if (diffMinutes < 60) return `${diffMinutes}m`;
    if (diffHours < 24) return `${diffHours}h`;
    return `${Math.floor(diffHours / 24)}d`;
  };

  const getSecurityColor = (security: number): string => {
    if (security >= 0.5) return 'var(--success)';
    if (security > 0) return 'var(--warning)';
    return 'var(--danger)';
  };

  const handleAlertClick = (battleId: number) => {
    navigate(`/battle/${battleId}`);
  };

  const fetchBattleDetails = useCallback(async (battleId: number) => {
    setDetailsLoading(true);
    try {
      const [battle, participants] = await Promise.all([
        battleApi.getBattle(battleId),
        battleApi.getBattleParticipants(battleId).catch(() => null),
      ]);

      // Participants API returns attackers with kills, defenders with losses
      const attackerAlliances = participants?.attackers?.alliances || [];
      const defenderAlliances = participants?.defenders?.alliances || [];
      const attackerCorps = participants?.attackers?.corporations || [];
      const defenderCorps = participants?.defenders?.corporations || [];

      setBattleDetails({
        battle_id: battle.battle_id,
        system_name: battle.system_name,
        region_name: battle.region_name,
        started_at: battle.started_at,
        last_kill_at: battle.last_kill_at,
        total_kills: battle.total_kills,
        total_isk_destroyed: battle.total_isk_destroyed,
        attackers: attackerAlliances.slice(0, 5).map((a: { alliance_id: number; alliance_name: string; kills?: number; isk_destroyed?: number }) => ({
          alliance_id: a.alliance_id,
          alliance_name: a.alliance_name,
          kills: a.kills || 0,
          isk_destroyed: a.isk_destroyed || 0,
          power_bloc: powerBlocCache?.get(a.alliance_id),
        })),
        defenders: defenderAlliances.slice(0, 5).map((d: { alliance_id: number; alliance_name: string; losses?: number; isk_lost?: number }) => ({
          alliance_id: d.alliance_id,
          alliance_name: d.alliance_name,
          kills: d.losses || 0,
          isk_destroyed: d.isk_lost || 0,
          power_bloc: powerBlocCache?.get(d.alliance_id),
        })),
        attacker_corps: attackerCorps.slice(0, 3).map((c: { corporation_id: number; corporation_name: string; alliance_id?: number; kills?: number; isk_destroyed?: number }) => ({
          corporation_id: c.corporation_id,
          corporation_name: c.corporation_name,
          alliance_id: c.alliance_id,
          kills: c.kills || 0,
          isk_destroyed: c.isk_destroyed || 0,
        })),
        defender_corps: defenderCorps.slice(0, 3).map((c: { corporation_id: number; corporation_name: string; alliance_id?: number; losses?: number; isk_lost?: number }) => ({
          corporation_id: c.corporation_id,
          corporation_name: c.corporation_name,
          alliance_id: c.alliance_id,
          kills: c.losses || 0,
          isk_destroyed: c.isk_lost || 0,
        })),
        top_ships: battle.top_ships || [],
      });
    } catch (err) {
      console.error('Error fetching battle details:', err);
      setBattleDetails(null);
    }
    setDetailsLoading(false);
  }, []);

  const handleAlertHover = (alert: TelegramAlert, e: React.MouseEvent) => {
    const rect = e.currentTarget.getBoundingClientRect();
    setTooltipPos({ x: rect.left + rect.width / 2, y: rect.top });
    setHoveredAlert(alert);
    setIsPaused(true);

    // Delay loading details to avoid excessive API calls
    if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
    hoverTimeoutRef.current = setTimeout(() => {
      fetchBattleDetails(alert.battle_id);
    }, 200);
  };

  const handleAlertLeave = () => {
    if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
    setHoveredAlert(null);
    setBattleDetails(null);
    setIsPaused(false);
  };

  if (loading) {
    return (
      <div style={{
        height: '36px',
        background: 'var(--bg-elevated)',
        borderRadius: '4px',
        display: 'flex',
        alignItems: 'center',
        padding: '0 1rem',
        color: 'var(--text-tertiary)',
        fontSize: '0.75rem'
      }}>
        Loading alerts...
      </div>
    );
  }

  if (alerts.length === 0) {
    return (
      <div style={{
        height: '36px',
        background: 'var(--bg-elevated)',
        borderRadius: '4px',
        display: 'flex',
        alignItems: 'center',
        padding: '0 1rem',
        color: 'var(--text-tertiary)',
        fontSize: '0.75rem'
      }}>
        📭 No recent alerts
      </div>
    );
  }

  // Duplicate alerts for seamless loop
  const duplicatedAlerts = [...alerts, ...alerts];

  return (
    <div
      style={{
        position: 'relative',
        overflow: 'hidden',
        background: 'var(--bg-elevated)',
        borderRadius: '4px',
        height: '36px',
      }}
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
    >
      {/* Gradient overlays for fade effect */}
      <div style={{
        position: 'absolute',
        left: 0,
        top: 0,
        bottom: 0,
        width: '40px',
        background: 'linear-gradient(to right, var(--bg-elevated), transparent)',
        zIndex: 2,
        pointerEvents: 'none',
      }} />
      <div style={{
        position: 'absolute',
        right: 0,
        top: 0,
        bottom: 0,
        width: '40px',
        background: 'linear-gradient(to left, var(--bg-elevated), transparent)',
        zIndex: 2,
        pointerEvents: 'none',
      }} />

      {/* Ticker content */}
      <div
        ref={tickerRef}
        style={{
          display: 'flex',
          alignItems: 'center',
          height: '100%',
          animation: isPaused ? 'none' : `ticker ${alerts.length * 2}s linear infinite`,
          whiteSpace: 'nowrap',
        }}
      >
        {duplicatedAlerts.map((alert, index) => {
          const topAlliance = alert.attackers?.[0] || alert.victims?.[0];

          return (
            <div
              key={`${alert.battle_id}-${alert.telegram_message_id}-${index}`}
              onClick={() => handleAlertClick(alert.battle_id)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0 1.5rem',
                cursor: 'pointer',
                borderRight: '1px solid var(--border-color)',
                height: '100%',
                transition: 'background 0.2s',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.06)'; handleAlertHover(alert, e); }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; handleAlertLeave(); }}
            >
              {/* Icon + Label */}
              <span style={{ fontSize: '0.9rem' }}>{getAlertIcon(alert.alert_type)}</span>
              <span style={{
                fontSize: '0.65rem',
                fontWeight: 700,
                padding: '0.15rem 0.3rem',
                borderRadius: '3px',
                background: alert.alert_type === 'new_battle' ? 'rgba(248, 81, 73, 0.2)' :
                           alert.alert_type === 'milestone' ? 'rgba(88, 166, 255, 0.2)' :
                           'rgba(63, 185, 80, 0.2)',
                color: alert.alert_type === 'new_battle' ? 'var(--danger)' :
                       alert.alert_type === 'milestone' ? 'var(--accent-blue)' :
                       'var(--success)',
              }}>
                {getAlertLabel(alert)}
              </span>

              {/* System + Security */}
              <span style={{ fontWeight: 600, fontSize: '0.8rem', color: 'var(--text-primary)' }}>
                {alert.system_name}
              </span>
              <span style={{
                fontSize: '0.7rem',
                color: getSecurityColor(alert.security),
                fontWeight: 600,
              }}>
                ({alert.security?.toFixed(1)})
              </span>

              {/* Region */}
              <span style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)' }}>
                {alert.region_name}
              </span>

              {/* Stats */}
              <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                {alert.total_kills} kills
              </span>
              <span style={{ fontSize: '0.75rem', color: 'var(--danger)', fontFamily: 'monospace' }}>
                {formatISK(alert.total_isk_destroyed)}
              </span>

              {/* Top Alliance Logo */}
              {topAlliance && (
                <img
                  src={`https://images.evetech.net/alliances/${topAlliance.alliance_id}/logo?size=32`}
                  alt=""
                  style={{ width: 20, height: 20, borderRadius: 2 }}
                  onError={(e) => { e.currentTarget.style.display = 'none'; }}
                />
              )}

              {/* Time */}
              <span style={{ fontSize: '0.65rem', color: 'var(--text-tertiary)' }}>
                {formatRelativeTime(alert.sent_at)}
              </span>
            </div>
          );
        })}
      </div>

      {/* CSS Animation */}
      <style>{`
        @keyframes ticker {
          0% { transform: translateX(0); }
          100% { transform: translateX(-50%); }
        }
      `}</style>

      {/* Hover Tooltip - Compact */}
      {hoveredAlert && (
        <div
          style={{
            position: 'fixed',
            left: Math.min(tooltipPos.x, window.innerWidth - 380),
            top: tooltipPos.y - 8,
            transform: 'translateX(-50%) translateY(-100%)',
            background: 'rgba(8, 12, 20, 0.98)',
            border: '1px solid rgba(100, 150, 255, 0.25)',
            borderRadius: '6px',
            padding: '0.5rem',
            width: '360px',
            zIndex: 1000,
            boxShadow: '0 4px 20px rgba(0,0,0,0.6)',
            pointerEvents: 'none',
            fontSize: '0.6rem',
          }}
        >
          {/* Header Row */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.35rem' }}>
            <span style={{ fontWeight: 700, fontSize: '0.75rem', color: '#fff' }}>{hoveredAlert.system_name}</span>
            <span style={{ color: getSecurityColor(hoveredAlert.security), fontWeight: 600 }}>
              {hoveredAlert.security?.toFixed(1)}
            </span>
            <span style={{ color: 'rgba(255,255,255,0.3)' }}>•</span>
            <span style={{ color: 'rgba(255,255,255,0.5)' }}>{hoveredAlert.region_name}</span>
            <span style={{ marginLeft: 'auto', display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
              <span style={{ color: '#ff4444', fontWeight: 700 }}>{hoveredAlert.total_kills}</span>
              <span style={{ color: 'rgba(255,255,255,0.3)' }}>kills</span>
              <span style={{ color: '#ffcc00', fontWeight: 700 }}>{formatISK(hoveredAlert.total_isk_destroyed)}</span>
              {battleDetails?.started_at && (
                <span style={{ color: 'rgba(255,255,255,0.4)', marginLeft: '0.2rem' }}>
                  {formatDuration(battleDetails.started_at, battleDetails.last_kill_at)}
                </span>
              )}
              <span style={{
                padding: '1px 4px',
                borderRadius: '2px',
                fontSize: '0.55rem',
                fontWeight: 700,
                background: hoveredAlert.status === 'active' ? 'rgba(255,68,68,0.3)' : 'rgba(0,255,136,0.2)',
                color: hoveredAlert.status === 'active' ? '#ff6666' : '#00ff88',
              }}>
                {hoveredAlert.status === 'active' ? 'LIVE' : 'END'}
              </span>
            </span>
          </div>

          {detailsLoading ? (
            <div style={{ color: 'rgba(255,255,255,0.4)', padding: '0.25rem 0' }}>Loading...</div>
          ) : battleDetails ? (
            <>
              {/* Two Column: Attackers vs Defenders */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.4rem' }}>
                {/* Attackers */}
                <div style={{ background: 'rgba(255,68,68,0.08)', borderRadius: '4px', padding: '0.3rem' }}>
                  <div style={{ color: '#ff4444', fontWeight: 700, marginBottom: '0.2rem', display: 'flex', justifyContent: 'space-between' }}>
                    <span>ATTACKERS</span>
                    <span style={{ color: '#ffcc00' }}>{formatISK(battleDetails.attackers?.reduce((s, a) => s + (a.isk_destroyed || 0), 0) || 0)}</span>
                  </div>
                  {battleDetails.attackers?.slice(0, 4).map((a, i) => (
                    <div key={a.alliance_id || i} style={{ marginBottom: '0.15rem' }}>
                      {a.power_bloc && (
                        <div style={{ fontSize: '0.5rem', color: '#a855f7', marginBottom: '0.05rem' }}>{a.power_bloc}</div>
                      )}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
                        <img src={`https://images.evetech.net/alliances/${a.alliance_id}/logo?size=32`} alt="" style={{ width: 12, height: 12, borderRadius: 2 }} onError={(e) => { e.currentTarget.style.display = 'none'; }} />
                        <span style={{ color: '#fff', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{a.alliance_name}</span>
                        <span style={{ color: '#00ff88', fontFamily: 'monospace' }}>{a.kills}</span>
                      </div>
                    </div>
                  ))}
                  {(battleDetails.attackers?.length || 0) > 4 && (
                    <div style={{ color: 'rgba(255,255,255,0.3)', fontSize: '0.5rem' }}>+{(battleDetails.attackers?.length || 0) - 4} alliances</div>
                  )}
                  {battleDetails.attacker_corps?.length > 0 && (
                    <div style={{ marginTop: '0.2rem', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '0.15rem' }}>
                      <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)', marginBottom: '0.1rem' }}>CORPS</div>
                      {battleDetails.attacker_corps.map((c, i) => (
                        <div key={c.corporation_id || i} style={{ display: 'flex', alignItems: 'center', gap: '0.2rem', fontSize: '0.55rem' }}>
                          <img src={`https://images.evetech.net/corporations/${c.corporation_id}/logo?size=32`} alt="" style={{ width: 10, height: 10, borderRadius: 1 }} onError={(e) => { e.currentTarget.style.display = 'none'; }} />
                          <span style={{ color: 'rgba(255,255,255,0.7)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.corporation_name}</span>
                          <span style={{ color: '#00ff88', fontFamily: 'monospace' }}>{c.kills}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                {/* Defenders */}
                <div style={{ background: 'rgba(0,212,255,0.08)', borderRadius: '4px', padding: '0.3rem' }}>
                  <div style={{ color: '#00d4ff', fontWeight: 700, marginBottom: '0.2rem', display: 'flex', justifyContent: 'space-between' }}>
                    <span>DEFENDERS</span>
                    <span style={{ color: '#ffcc00' }}>{formatISK(battleDetails.defenders?.reduce((s, d) => s + (d.isk_destroyed || 0), 0) || 0)}</span>
                  </div>
                  {battleDetails.defenders?.slice(0, 4).map((d, i) => (
                    <div key={d.alliance_id || i} style={{ marginBottom: '0.15rem' }}>
                      {d.power_bloc && (
                        <div style={{ fontSize: '0.5rem', color: '#a855f7', marginBottom: '0.05rem' }}>{d.power_bloc}</div>
                      )}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
                        <img src={`https://images.evetech.net/alliances/${d.alliance_id}/logo?size=32`} alt="" style={{ width: 12, height: 12, borderRadius: 2 }} onError={(e) => { e.currentTarget.style.display = 'none'; }} />
                        <span style={{ color: '#fff', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{d.alliance_name}</span>
                        <span style={{ color: '#ff4444', fontFamily: 'monospace' }}>{d.kills}</span>
                      </div>
                    </div>
                  ))}
                  {(battleDetails.defenders?.length || 0) > 4 && (
                    <div style={{ color: 'rgba(255,255,255,0.3)', fontSize: '0.5rem' }}>+{(battleDetails.defenders?.length || 0) - 4} alliances</div>
                  )}
                  {battleDetails.defender_corps?.length > 0 && (
                    <div style={{ marginTop: '0.2rem', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '0.15rem' }}>
                      <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)', marginBottom: '0.1rem' }}>CORPS</div>
                      {battleDetails.defender_corps.map((c, i) => (
                        <div key={c.corporation_id || i} style={{ display: 'flex', alignItems: 'center', gap: '0.2rem', fontSize: '0.55rem' }}>
                          <img src={`https://images.evetech.net/corporations/${c.corporation_id}/logo?size=32`} alt="" style={{ width: 10, height: 10, borderRadius: 1 }} onError={(e) => { e.currentTarget.style.display = 'none'; }} />
                          <span style={{ color: 'rgba(255,255,255,0.7)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.corporation_name}</span>
                          <span style={{ color: '#ff4444', fontFamily: 'monospace' }}>{c.kills}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Ships Row */}
              {battleDetails.top_ships && battleDetails.top_ships.length > 0 && (
                <div style={{ display: 'flex', gap: '0.3rem', marginTop: '0.3rem', flexWrap: 'wrap', alignItems: 'center' }}>
                  <span style={{ color: 'rgba(255,255,255,0.3)' }}>SHIPS:</span>
                  {battleDetails.top_ships.slice(0, 6).map((s, i) => (
                    <span key={i} style={{ color: '#a855f7', background: 'rgba(168,85,247,0.1)', padding: '0 3px', borderRadius: '2px' }}>
                      {s.ship_name} <span style={{ color: 'rgba(255,255,255,0.4)' }}>×{s.count}</span>
                    </span>
                  ))}
                </div>
              )}
            </>
          ) : (
            /* Fallback - using telegram alert data with powerbloc info */
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.3rem' }}>
              {hoveredAlert.attackers && hoveredAlert.attackers.length > 0 && (
                <div style={{ background: 'rgba(255,68,68,0.08)', borderRadius: '4px', padding: '0.3rem' }}>
                  <div style={{ color: '#ff4444', fontWeight: 700, marginBottom: '0.15rem' }}>ATTACKERS</div>
                  {hoveredAlert.attackers.slice(0, 5).map((a, i) => (
                    <div key={a.alliance_id || i} style={{ marginBottom: '0.15rem' }}>
                      {a.powerbloc && (
                        <div style={{ fontSize: '0.5rem', color: '#a855f7', marginBottom: '0.05rem' }}>{a.powerbloc}</div>
                      )}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
                        <img src={`https://images.evetech.net/alliances/${a.alliance_id}/logo?size=32`} alt="" style={{ width: 12, height: 12, borderRadius: 2 }} onError={(e) => { e.currentTarget.style.display = 'none'; }} />
                        <span style={{ color: '#fff', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{a.alliance_name}</span>
                        <span style={{ color: '#00ff88', fontFamily: 'monospace', fontSize: '0.55rem' }}>{a.kills}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
              {hoveredAlert.victims && hoveredAlert.victims.length > 0 && (
                <div style={{ background: 'rgba(0,212,255,0.08)', borderRadius: '4px', padding: '0.3rem' }}>
                  <div style={{ color: '#00d4ff', fontWeight: 700, marginBottom: '0.15rem' }}>DEFENDERS</div>
                  {hoveredAlert.victims.slice(0, 5).map((v, i) => (
                    <div key={v.alliance_id || i} style={{ marginBottom: '0.15rem' }}>
                      {v.powerbloc && (
                        <div style={{ fontSize: '0.5rem', color: '#a855f7', marginBottom: '0.05rem' }}>{v.powerbloc}</div>
                      )}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
                        <img src={`https://images.evetech.net/alliances/${v.alliance_id}/logo?size=32`} alt="" style={{ width: 12, height: 12, borderRadius: 2 }} onError={(e) => { e.currentTarget.style.display = 'none'; }} />
                        <span style={{ color: '#fff', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{v.alliance_name}</span>
                        <span style={{ color: '#ff4444', fontFamily: 'monospace', fontSize: '0.55rem' }}>{v.losses}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function formatDuration(start: string, end: string): string {
  const startTime = new Date(start).getTime();
  const endTime = new Date(end).getTime();
  const diffMs = endTime - startTime;
  if (diffMs < 0) return 'ongoing';
  const hours = Math.floor(diffMs / (1000 * 60 * 60));
  const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}
